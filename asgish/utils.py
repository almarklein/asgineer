"""
Some utilities for common tasks.
"""

import gzip
import hashlib
import mimetypes

from ._app import normalize_response


__all__ = ["normalize_response", "make_asset_handler"]


def make_asset_handler(assets, max_age=0, min_compress_size=256):
    """
    Get a coroutine function for efficiently serving in-memory assets.
    The resulting handler functon takes care of setting the appropriate
    content-type header, sending compressed responses when possible, and
    applying appropriate HTTP caching (using etag and cache-control headers).
    Usage:
    
    .. code-block:: python
    
        assets = ... # a dict mapping filenames to asset bodies (str/bytes)
        
        asset_handler = make_asset_handler(assets)
        
        async def some_handler(request):
            path = request.path.lstrip("/")
            return await asset_handler(request, path)
    
    
    Parameters for ``make_asset_handler()``:
    
    * ``assets (dict)``: The assets to serve. The keys represent "file names"
      and must be str. The values must be bytes or str.
    * ``max_age (int)``: The maximum age of the assets. This is used as a hint
      for the client (e.g. the browser) for how long an asset is "fresh"
      and can be used before validating it. The default is zero. Can be
      set higher for assets that hardly ever change (e.g. images and fonts).
    * ``min_compress_size (int)``: The minimum size of the body for compressing
      an asset. Default 256.
    
    Parameters for the handler:
    
    * ``request (Request)``: The Asgineer request object (for the request headers).
    * ``path (str)``: A key in the asset dictionary. Case insensitive.
      If not given or None, ``request.path.lstrip("/")`` is used.
    
    Handler behavior:
    
    * If the given path is not present in the asset dict (case insensitive),
      a 404-not-found response is returned.
    * The ``etag`` header is set to a (sha256) hash of the body of the asset.
    * The ``cache-control`` header is set to "public must-revalidate max-age=xx".
    * If the request has a ``if-none-match`` header that matches the etag,
      the handler responds with 304 (indicating to the client that the resource
      is still up-to-date).
    * Otherwise, the asset body is returned, setting the ``content-type`` header
      based on the filename extensions of the keys in the asset dicts. If the
      key does not contain a dot, the ``content-type`` will be based on the
      body of the asset.
    * If the asset is over ``min_compress_size`` bytes, and the request
      has a ``accept-encoding`` header that contains "gzip", the data
      is send in compressed form.
    """

    if not isinstance(assets, dict):
        raise TypeError("make_asset_handler() expects a dict of assets")
    assert isinstance(max_age, int) and max_age >= 0

    # Copy the dict, store hashes, prepare zipped data
    assets = dict((key.lower(), val) for (key, val) in assets.items())
    hashes = {}
    zipped = {}
    ctypes = {}
    for key, val in assets.items():
        # Get binary body
        if isinstance(val, bytes):
            bbody = val
        elif isinstance(val, str):
            bbody = val.encode()
        else:
            raise ValueError("Asset bodies must be str or bytes.")
        # Store hash
        hashes[key] = hashlib.sha256(bbody).hexdigest()
        # Store zipped version if above limit
        if len(bbody) >= min_compress_size:
            zipped[key] = gzip.compress(bbody)
        # Store mimetype
        ctype, enc = mimetypes.guess_type(key)
        if ctype:
            ctypes[key] = ctype
        elif isinstance(val, bytes):
            ctypes[key] = "application/octet-stream"
        else:
            pass  # str bodies get a content-type from Asgineer core.

    async def asset_handler(request, path=None):
        assert request.method in ("GET", "HEAD")
        if path is None:
            path = request.path.lstrip("/")
        path = path.lower()

        # Exit early on 404
        if path not in assets:
            return 404, {}, "404 not found"

        content_etag = hashes.get(path, None)
        request_etag = request.headers.get("if-none-match", None)
        headers = {
            "etag": content_etag,
            "cache-control": f"public must-revalidate max-age={max_age:d}",
        }

        # If client already has the exact asset, send confirmation now
        if request_etag and request_etag == content_etag:
            return 304, headers, b""

        # Set content type
        if path in ctypes:
            headers["content-type"] = ctypes[path]

        # Get body, zip if we should and can
        if path in zipped and "gzip" in request.headers.get("accept-encoding", ""):
            headers["content-encoding"] = "gzip"
            body = zipped[path]
        else:
            body = assets[path]

        return 200, headers, body

    return asset_handler
