"""
Demonstrate websocket usage.
"""

import asgish


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
        console.log(m.data);
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


@asgish.to_asgi
async def main(request):

    if not request.path.rstrip("/"):
        return index  # Asgish sets the text/html content type
    elif request.path.startswith("/ws"):
        return await websocket_handler(request)
    else:
        return 404, {}, f"404 not found {request.path}"


async def websocket_handler(request):
    assert request.scope["type"] == "websocket", "Expected ws"
    print("request", request)

    await request.accept()
    await request.send("hello!")

    async for m in request.receive_iter():
        await request.send("echo: " + str(m))
        print(m)

    print("done")
    # The moment that we return, the websocket will be closed
    # (if the ASGI server behaves correctly)


if __name__ == "__main__":
    asgish.run(main, "uvicorn", "localhost:80", log_level="info")
