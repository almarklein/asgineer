"""
Demonstrate websocket usage.
"""

from asgish import handler2asgi, run


index = """
<!DOCTYPE html>
<html>
<meta><meta charset='UTF-8'></meta>
<body>
Open console, and use "ws.send('x')" to send a message to the server.

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
</body>
</html>
""".lstrip()


@handler2asgi
async def main(request):

    if not request.path.rstrip("/"):
        return index  # asgish sets the text/html content type
    elif request.path.startswith("/ws"):
        return await websocket_handler(request)
    else:
        return 404, {}, f"404 not found {request.path}"


async def websocket_handler(request):
    assert request.scope["type"] == "websocket", "Expected ws"
    print("request", request)

    await request.accept()  # todo: server part can do this?
    await request.send("hello!")

    async def waiter():
        async for m in request.receive_iter():
            print(m)
        print("done")

    import asyncio

    await asyncio.create_task(waiter())
    # The moment that we return, the websocket will be closed
    # (if the ASGI server behaves correctly)


if __name__ == "__main__":
    run(main, "uvicorn", "localhost:80", log_level="info")
