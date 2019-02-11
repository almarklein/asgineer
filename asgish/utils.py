"""
Some utilities for common tasks.
"""

import gzip
import hashlib
import mimetypes


def make_asset_handler(assets, max_age=0, min_zip_size=500):
    """
    Get a coroutine function that can be used to serve the given assets.
    It's signature is ``asset_handler(request, path=None)``. If path is not
    given or None, ``request.path.lstrip("/")`` is used.
    
    This function takes care of sending compressed responses, and
    applying appropriate HTTP caching. The ETag header is used so that
    clients can validate the asset, and the handler will send back only
    a small confirmation if the asset has not changed.
    
    This function makes is easy to create a reliable and fast asset
    handler. It may, however, be less suited for large data, since all
    assets are stored in-memory.
    
    Parameters
        assets (dict): The assets to server. The keys must be str (this function
            takes care of making it case insensitive). The values must be bytes
            or str.
        max_age (int): The maximum age of the assets. This is used as a hint
            for the client (e.g. the browser) for how long an asset is "fresh"
            and can be used before validating it. The default is zero. Can be
            set higher for assets that hardly ever change (e.g. images). Note
            that some browsers top this value at 36000 (10 minutes).
        min_zip_size (int): The minimum size of the body for zipping an asset.
            Note that responses are only zipped if the request indicates that
            the client can deal with zipped data.
    """

    if not isinstance(assets, dict):
        raise TypeError("make_asset_handler() expects a dict of assets")
    assert isinstance(max_age, int) and max_age >= 0

    # Copy the dict, store hashes, prepare zipped data
    assets = dict((key.lower(), val) for (key, val) in assets.items())
    hashes = {}
    zipped = {}
    for key, val in assets.items():
        if isinstance(val, bytes):
            bbody = val
        elif isinstance(val, str):
            bbody = val.encode()
        else:
            raise ValueError("Asset bodies must be str or bytes.")
        hashes[key] = hashlib.sha256(bbody).hexdigest()
        if len(bbody) >= min_zip_size:
            zipped[key] = gzip.compress(bbody)

    async def asset_handler(request, path=None):
        assert request.method in ("GET", "HEAD")
        if path is None:
            path = request.path.lstrip("/")

        # Exit early on 404
        if path not in assets:
            return 404, {}, b""

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
        ctype, enc = mimetypes.guess_type(path)
        if ctype:
            headers["content-type"] = ctype

        # Get body, zip if we should and can
        if path in zipped and "gzip" in request.headers.get("accept-encoding", ""):
            headers["content-encoding"] = "gzip"
            body = zipped[path]
        else:
            body = assets[path]

        return 200, headers, body

    return asset_handler
