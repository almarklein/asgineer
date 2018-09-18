from asgish import handler2asgi

index = """
<html>
    <a href='/api/items'>item api</a><br>
    <a href='/redirect?url=http://python.org'>redirect</a><br>
</html>
"""


@handler2asgi
async def main(request):

    if not request.path.rstrip("/"):
        return {"content-type": "text/html"}, index
    elif request.path.startswith("/api/"):
        return await api(request)
    elif request.path == "/redirect":
        return await redirect(request)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(main, host="127.0.0.1", port=8080)
