"""
Demonstrate the use of Starlette middleware to Asgineer handlers.

Because Asgineer produces an ASGI-compatible application class, we can
wrap it with ASGI middleware, e.g. from Starlette. Hooray for standards!
"""

import asgineer

from starlette.middleware.gzip import GZipMiddleware


@asgineer.to_asgi
async def main(req):
    return "hello world " * 1000


# All requests that have a body over 1 KiB will be zipped
main = GZipMiddleware(main, minimum_size=1024)


if __name__ == "__main__":
    asgineer.run("__main__:main", "uvicorn")
