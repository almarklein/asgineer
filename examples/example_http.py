"""
Example web app written in Asgineer. We have one main handler, which may
delegate the request to one of the other handlers, which demonstrate a
few different ways to send an http response.
"""

import asgineer

index = """
<!DOCTYPE html>
<html>
<meta><meta charset='UTF-8'></meta>
<body>
    <a href='/foo.bin'>Bytes</a><br>
    <a href='/foo.txt'>Text</a><br>
    <a href='/api/items'>JSON api</a><br>
    <a href='/redirect?url=http://python.org'>redirect</a><br>
    <a href='/error1'>error1</a><br>
    <a href='/error2'>error2</a><br>
    <a href='/chunks'>chunks</a><br>
</body>
</html>
""".lstrip()


@asgineer.to_asgi
async def main(request):

    if not request.path.rstrip("/"):
        return index  # Asgineer sets the text/html content type
    elif request.path.endswith(".bin"):
        return await bytes_handler(request)
    elif request.path.endswith(".txt"):
        return await text_handler(request)
    elif request.path.startswith("/api/"):
        return await json_api(request)
    elif request.path == "/redirect":
        return await redirect(request)
    elif request.path == "/error1":
        return await error1(request)
    elif request.path == "/error2":
        return await error2(request)
    elif request.path == "/chunks":
        return await chunks(request)
    else:
        return 404, {}, f"404 not found {request.path}"


async def bytes_handler(request):
    """Returning bytes; a response in its purest form."""
    return b"x" * 42


async def text_handler(request):
    """Returning a string causes the content-type to default to text/plain.
    Note that the main handler also returns a string, but gets a text/html
    content-type because it starts with "<!DOCTYPE html>" or "<html>".
    """
    return "Hello world"


async def json_api(request):
    """Returning a dict will cause the content-type to default to
    application/json.
    """
    return {
        "this": "is",
        "the": "api",
        "method": request.method,
        "apipath": request.path[4:],
    }


async def redirect(request):
    """Handler to do redirects using HTTP status code 307.
    The url to redirect to must be given with a query parameter:
    http://localhost/redirect?url=http://example.com
    """
    url = request.querydict.get("url", "")
    if url:
        return 307, {"location": url}, "Redirecting"
    else:
        return 500, {}, "specify the URL using a query param"


async def error1(request):
    """Handler with a deliberate error."""

    def foo():
        1 / 0

    foo()


async def error2(request):
    """Handler with a deliberate wrong result."""
    return 400, "ho"


async def chunks(request):
    """A handler that sends chunks at a slow pace.
    The browser will download the page over the range of 2 seconds,
    but only displays it when done. This e.g. allows streaming large
    files without using large amounts of memory.
    """

    async def iter():
        yield "<html><head></head><body>"
        yield "Here are some chunks dripping in:<br>"
        for i in range(20):
            await asgineer.sleep(0.1)
            yield "CHUNK <br>"
        yield "</body></html>"

    return 200, {"content-type": "text/html"}, iter()


if __name__ == "__main__":
    # asgineer.run(main, "hypercorn", "localhost:8080", workers=3)
    asgineer.run(main, "uvicorn", "localhost:8080")
