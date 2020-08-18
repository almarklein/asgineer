"""
Example chat application using websockets.

The handler is waiting for a message most of the time. When it receives
one, it sends it to all other websockets. When the websocket
disconnects, request.receive() raises DisconnectedError and the handler
exits. The request is automatically removed from waiting_requests
(that's the point of RequestSet).
"""

import asgineer


waiting_requests = asgineer.RequestSet()


@asgineer.to_asgi
async def main(request):
    if request.path == "/":
        return HTML_TEMPLATE
    elif request.path == "/ws":
        await request.accept()
        await ws_handler(request)
    else:
        return 404, {}, "not found"


async def ws_handler(request):
    waiting_requests.add(request)
    while True:
        msg = await request.receive()  # raises DisconnectedError on disconnect
        for r in waiting_requests:
            await r.send(msg)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Asgineer WS chat example</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<script>
ws = new WebSocket('ws://' + window.location.host + '/ws');
ws.onmessage = function(m) {
    var el = document.getElementById("messages");
    el.innerHTML += m.data + "<br>";
}

window.onload = function () {
    var textinput = document.getElementById("text");
    textinput.value = '';
    var button = document.getElementById("button");
    button.onclick = function () {
        if (textinput.value) {
            ws.send(textinput.value);
            textinput.value = '';
        }
    }
}
</script>

<style>
html { height: 100%; }
body { height: 100%; padding: 0; }
body, .main, .messages, .userinput { margin: 0; }
.main { position: absolute; top:0; bottom:0; width: 600px; left: calc(50% - 300px); }
.messages, .userinput { background: #def; border-radius: 5px; padding: 5px; margin-top: 5px; }
.messages { height: calc(100% - 100px); overflow-y: scroll; }
.userinput { height: 45px; }
.userinput > input { height: 45px; border-radius: 5px; box-sizing:border-box; }
.userinput > input[type=text] { width: 500px; }
.userinput > input[type=button] { width: 80px; }
}
</style>

<div class='main'>
    <div class="messages" id="messages"></div>
    <div class="userinput">
        <input type='text' id='text' placeholder='Your message ...' />
        <input type='button' id='button' value='Send' />
    </div>
</div>

</body>
</html>
""".lstrip()


if __name__ == "__main__":
    asgineer.run(main, "uvicorn", "localhost:80")
