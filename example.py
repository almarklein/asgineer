import asyncio

from asgish import handler2asgi

index = """
<html>
    <a href='/api/items'>item api</a><br>
    <a href='/chunks'>chunks</a><br>
    <a href='/redirect?url=http://python.org'>redirect</a><br>
    
</html>
""".lstrip()


@handler2asgi
async def main(request):

    if not request.path.rstrip("/"):
        return index  # asgish sets the text/html content type
    elif request.path.startswith("/api/"):
        return await api(request)
    elif request.path == "/redirect":
        return await redirect(request)
    elif request.path == "/chunks":
        return await chunks(request)
    else:
        return 404, {}, "404 not found"


async def api(request):
    """ Handler for the API.
    """
    return {
        "this": "is",
        "the": "api",
        "method": request.method,
        "apipath": request.path[4:],
    }


async def redirect(request):
    """ Handler to do redirects using http 307.
    The url to redirect to must be given with a query parameter:
    http://localhost/redirect?url=http://example.com
    """
    url = request.querydict.get("url", "")
    if url:
        return 307, {"Location": url}, "Redirecting"
    else:
        return 500, {}, "specify the URL using a query param"


async def chunks(request):
    """ A handler that sends chunks at a slow pace.
    The browser will download the page over the range of 2 seconds,
    but only displays it when done. This e.g. allows streaming large
    files without using large amounts of memory.
    """

    async def iter():
        yield "<html><head></head><body>"
        yield "Here are some chunks dripping in:<br>"
        for i in range(20):
            await asyncio.sleep(0.1)
            yield "CHUNK <br>"
        yield "</body></html>"

    return 200, {"content-type": "text/html"}, iter()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(main, host="127.0.0.1", port=8080)
