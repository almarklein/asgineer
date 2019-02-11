"""
This might well be the fastest way to host a static website, because:

* Uvicorn (with uvloop) is lighning fast.
* Asgish is just a minimal layer on top.
* The ``make_asset_handler()`` takes care of HTTP caching and compression.

"""

import asgish


# Define a dictionary of assets. Change this to e.g. load them from the
# file system, generate with Flexx, or whatever way you like.
assets = {
    "index.html": "<html><a href='foo.html'>bar</a> or <a href='bar.html'>bar</a></html>",
    "foo.html": "<html>This is foo, there is also <a href='bar.html'>bar</a></html>",
    "bar.html": "<html>This is bar, there is also <a href='foo.html'>foo</a></html>",
}


# Create a handler to server them
asset_handler = asgish.utils.make_asset_handler(assets)


@asgish.to_asgi
async def main(request):
    path = request.path.lstrip("/") or "index.html"
    return await asset_handler(request, path)


if __name__ == "__main__":
    asgish.run(main, "uvicorn", "localhost:8080")
