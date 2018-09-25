"""
Example web app written in asgish. We have one main handler, which may
delegate the request to one of the other handlers, which demonstrate a
few different ways to send an http response.
"""

import sys

from asgish import handler2asgi, run

index = """
<!DOCTYPE html>
<html>
<meta><meta charset='UTF-8'></meta>
<body>
    <a href='/foo.bin'>Bytes</a><br>
    <a href='/foo.txt'>Text</a><br>
    <a href='/api/items'>JSON api</a><br>
    <a href='/chunks'>chunks</a><br>
    <a href='/redirect?url=http://python.org'>redirect</a><br>
</body>
</html>
""".lstrip()


@handler2asgi
async def main(request):

    if not request.path.rstrip("/"):
        return index  # asgish sets the text/html content type
    elif request.path.endswith(".txt"):
        return await text_handler(request)
    elif request.path.endswith(".bin"):
        return await bytes_handler(request)
    elif request.path.startswith("/api/"):
        return await json_api(request)
    elif request.path == "/redirect":
        return await redirect(request)
    elif request.path == "/chunks":
        return await chunks(request)
    else:
        return 404, {}, f"404 not found {request.path}"


async def text_handler(request):
    """ Returning a string causes the content-type to default to text/plain.
    Note that the main handler also returns a string, but gets a text/html
    content-type because it starts with "<!DOCTYPE html>" or "<html>".
    """
    return "Hello world"


async def bytes_handler(request):
    """ Returning bytes; a response in its purest form.
    """
    return b"x" * 42


async def json_api(request):
    """ Returning a dict will cause the content-type to default to
    application/json.
    """
    return {
        "this": "is",
        "the": "api",
        "method": request.method,
        "apipath": request.path[4:],
    }


async def redirect(request):
    """ Handler to do redirects using HTTP status code 307.
    The url to redirect to must be given with a query parameter:
    http://localhost/redirect?url=http://example.com
    """
    url = request.querydict.get("url", "")
    if url:
        return 307, {"location": url}, "Redirecting"
    else:
        return 500, {}, "specify the URL using a query param"


async def chunks(request):
    """ A handler that sends chunks at a slow pace.
    The browser will download the page over the range of 2 seconds,
    but only displays it when done. This e.g. allows streaming large
    files without using large amounts of memory.
    """
    # Little triage to support both Trio and asyncio based apps
    if "trio" in sys.modules:
        import trio as aio
    else:
        import asyncio as aio

    async def iter():
        yield "<html><head></head><body>"
        yield "Here are some chunks dripping in:<br>"
        for i in range(20):
            await aio.sleep(0.1)
            yield "CHUNK <br>"
        yield "</body></html>"

    return 200, {"content-type": "text/html"}, iter()


if __name__ == "__main__":
    run(main, server="uvicorn", bind="localhost:80", log_level="info")
