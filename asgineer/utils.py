"""
Some utilities for common tasks.
"""

import gzip
import hashlib
import mimetypes

from ._app import normalize_response, guess_content_type_from_body
from ._compat import sleep

__all__ = [
    "sleep",
    "normalize_response",
    "make_asset_handler",
    "guess_content_type_from_body",
]

VIDEO_EXTENSIONS = ".mp4", ".3gp", ".webm"


def make_asset_handler(assets, max_age=0, min_compress_size=256):
    """
    Get a coroutine function for efficiently serving in-memory assets.
    The resulting handler functon takes care of setting the appropriate
    content-type header, sending compressed responses when
    possible/sensible, and applying appropriate HTTP caching (using
    etag and cache-control headers). Usage:

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
    * The ``cache-control`` header is set to "public, must-revalidate, max-age=xx".
    * If the request has a ``if-none-match`` header that matches the etag,
      the handler responds with 304 (indicating to the client that the resource
      is still up-to-date).
    * Otherwise, the asset body is returned, setting the ``content-type`` header
      based on the filename extensions of the keys in the asset dicts. If the
      key does not contain a dot, the ``content-type`` will be based on the
      body of the asset.
    * If the asset is over ``min_compress_size`` bytes, is not a video, the
      request has a ``accept-encoding`` header that contains "gzip",
      and the compressed data is less that 90% of the raw data, the
      data is send in compressed form.
    """

    if not isinstance(assets, dict):
        raise TypeError("make_asset_handler() expects a dict of assets")
    if not (isinstance(max_age, int) and max_age >= 0):  # pragma: no cover
        raise TypeError("make_asset_handler() max_age must be a positive int")

    # Store etags, prepare unzipped/zipped bodies, store ctypes
    etags = {}
    unzipped = {}
    zipped = {}
    ctypes = {}
    for path, body in assets.items():
        # Get lowercase path
        lpath = path.lower()
        # Get binary body
        if isinstance(body, bytes):
            bbody = body
        elif isinstance(body, str):
            bbody = body.encode()
        else:
            raise ValueError("Asset bodies must be bytes or str.")
        # Store etag
        etags[lpath] = hashlib.sha256(bbody).hexdigest()
        # Store unzipped body
        unzipped[lpath] = bbody
        # Store zipped body if it makes sense
        if len(bbody) >= min_compress_size:
            if not lpath.endswith(VIDEO_EXTENSIONS):
                bbody_zipped = gzip.compress(bbody)
                if len(bbody_zipped) < 0.90 * len(bbody):
                    zipped[lpath] = bbody_zipped
        # Store ctype
        ctype, _ = mimetypes.guess_type(lpath)
        if ctype:
            ctypes[lpath] = ctype
        else:
            ctypes[lpath] = guess_content_type_from_body(body)

    async def asset_handler(request, path=None):
        if request.method not in ("GET", "HEAD"):
            return 405, {}, "Method not allowed"

        if path is None:
            path = request.path.lstrip("/")
        path = path.lower()

        if path not in unzipped:
            return 404, {}, "File not found"

        assert path in etags
        assert path in ctypes

        status = 200
        body = unzipped[path]
        headers = {}
        headers["cache-control"] = f"public, must-revalidate, max-age={max_age:d}"
        headers["content-length"] = str(len(body))
        headers["content-type"] = ctypes[path]
        headers["etag"] = f'"{etags[path]}"'

        # Get body, zip if we should and can
        if "gzip" in request.headers.get("accept-encoding", "") and path in zipped:
            body = zipped[path]
            headers["content-encoding"] = "gzip"
            headers["content-length"] = str(len(body))

        # If client already has the exact asset, send confirmation now
        if request.headers.get("if-none-match") == headers["etag"]:
            status = 304
            body = b""
            # https://www.rfc-editor.org/rfc/rfc7232#section-4.1
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            headers.pop("content-type", None)

        # The response to a head request should not include a body
        if request.method == "HEAD":
            body = b""

        # Note that we always return bytes, not a stream-response. The
        # assets used with this utility are assumed to be small-ish,
        # since they are in-memory.
        return status, headers, body

    return asset_handler
