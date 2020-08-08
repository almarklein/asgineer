"""
Example websocket app that echos websocket messages.
"""

import asgineer


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


@asgineer.to_asgi
async def main(request):

    if not request.path.rstrip("/"):
        return index  # Asgineer sets the text/html content type
    elif request.path.startswith("/ws"):
        assert request.scope["type"] == "websocket", "Expected ws"
        await request.accept()
        await websocket_handler(request)
    else:
        return 404, {}, f"404 not found {request.path}"


async def websocket_handler(request):
    print("request", request)
    await request.send("hello!")
    while True:
        m = await request.receive()
        await request.send("echo: " + str(m))
        print(m)

    print("done")


if __name__ == "__main__":
    asgineer.run(main, "uvicorn", "localhost:80")
