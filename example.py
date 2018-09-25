"""
Example web app written in asgish. We have one main handler, which may
delegate the request to one of the other handlers.
"""

import sys

from asgish import handler2asgi, run

index = """
<html>
    <a href='/serverinfo'>server info</a><br>
    <a href='/api/items'>item api</a><br>
    <a href='/chunks'>chunks</a><br>
    <a href='/redirect?url=http://python.org'>redirect</a><br>


<script>

window.onload = function() {
    window.ws = new WebSocket('ws://' + window.location.host + '/ws');
    window.ws.onmessage = function(m) {
        console.log(m);
    }
    window.ws.onerror = function (e) {
        console.log(e);
    }
    window.ws.onclose = function () {
        console.log('ws closed');
    }
}

</script>
</html>
""".lstrip()


@handler2asgi
async def main(request):
    
    if not request.path.rstrip("/"):
        return index  # asgish sets the text/html content type
    elif request.path.startswith("/ws"):
        return await websocket_handler(request)
    elif request.path.startswith("/serverinfo"):
        return await serverinfo(request)
    elif request.path.startswith("/api/"):
        return await api(request)
    elif request.path == "/redirect":
        return await redirect(request)
    elif request.path == "/chunks":
        return await chunks(request)
    else:
        return 404, {}, f"404 not found {request.path}"


async def websocket_handler(request):
    assert request.scope['type'] == 'websocket', 'Expected ws'
    print('request', request)
    
    await request.accept()  # todo: server part can do this?
    await request.send('hello!')
    
    async def waiter():
        async for m in request.receive_iter():
            print(m)
        print('done')
    
    import asyncio
    await asyncio.create_task(waiter())


async def serverinfo(request):
    """ Display some info on the server.
    """
    return f"{request.scope['server']}"


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

    # === Pick a server:
    # from daphne import run  # does not yet work
    #from hypercorn import run  # does not yet work
    # from trio_web import run
    # from uvicorn import run

    x = run(main, 'hypercorn', bind="127.0.0.1:80")
