"""
Example chat application using short polling, long polling and SSE.

In this setup, the long-polling and SSE requests are put to sleep,
and woken up when new data is available.

This approach works well for long polling, but not for websockets.
See example_ws_chat.py for a similar chat based on websockets. Note that
SSE could follow a more hybrid approach.
"""

import asgineer


@asgineer.to_asgi
async def main(request):
    if request.path == "/":
        return HTML_TEMPLATE.replace("POLL_METHOD", "none")
    elif request.path == "/short_poll":
        return HTML_TEMPLATE.replace("POLL_METHOD", "short_poll")
    elif request.path == "/long_poll":
        return HTML_TEMPLATE.replace("POLL_METHOD", "long_poll")
    elif request.path == "/sse":
        return HTML_TEMPLATE.replace("POLL_METHOD", "sse")
    elif request.path == "/say":
        message_bytes = await request.get_body(1024)
        await post_new_message(message_bytes.decode())
        return 200, {}, b""
    elif request.path.startswith("/messages/"):
        return await messages_handler(request)
    else:
        return 404, {}, "not found"


messages = []
waiting_requests = asgineer.RequestSet()


async def post_new_message(message):
    messages.append(message)
    messages[:-32] = []
    for r in waiting_requests:
        await r.wakeup()


async def messages_handler(request):
    poll_method = request.path.split("/", 2)[-1]

    if poll_method == "short_poll":
        # Short poll: simply respond with the messages.
        await request.accept(200, {"content-type": "text/plain"})
        await request.send("<br>".join(messages))

    elif poll_method == "long_poll":
        # Long poll: wait with sending messages until we have new data.
        waiting_requests.add(request)
        await request.accept(200, {"content-type": "text/plain"})
        await request.sleep_while_connected(3)
        await request.send("<br>".join(messages))

    elif poll_method == "sse":
        # Server Side Events: send messages each time we have new data.
        # Also need special headers.
        waiting_requests.add(request)
        sse_headers = {
            "content-type": "text/event-stream",
            "cache-control": "no-cache",
            "connection": "keep-alive",
        }
        await request.accept(200, sse_headers)
        while True:
            await request.sleep_while_connected(10)
            await request.send(f"event: message\ndata: {'<br>'.join(messages)}\n\n")

    else:
        raise ValueError(f"Invalid message handler endpoint: {request.path}")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Asgineer example polling: POLL_METHOD</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<script>
function set_text(text) {
    var el = document.getElementById("messages");
    el.innerHTML = text;
}


async function do_short_poll() {
    let response = await fetch("/messages/short_poll");
    if (response.status == 200) { set_text(await response.text()); }
}

async function do_long_poll() {
    let response = await fetch("/messages/long_poll");
    if (response.status == 200) {
        set_text(await response.text());
        do_long_poll(); // schedule a new long poll
    }
}

async function do_sse() {
    var evtSource = new EventSource("/messages/sse");
    evtSource.addEventListener("message", function(event) { set_text(event.data); });
}

window.onload = function () {
    // Do a short poll on startup
    do_short_poll();

    // Select polling scheme based on path
    var poll_method = 'POLL_METHOD';
    if (poll_method == 'short_poll') {
        setInterval(do_short_poll, 2000);
    } else if (poll_method == 'long_poll') {
        do_long_poll();
    } else if (poll_method == 'sse') {
        do_sse();
    }

    var textinput = document.getElementById("text");
    textinput.value = '';
    var button = document.getElementById("button");
    button.onclick = function () {
        if (textinput.value) {
            fetch("/say", {method: 'post', body: textinput.value});
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

<div style='padding: 15px'>
    Current polling method: POLL_METHOD<br /><br />
    <a href="/">No polling (only on page load)</a><br />
    <a href="/short_poll">Short Polling</a><br />
    <a href="/long_poll">Long Polling</a><br />
    <a href="/sse">Server Side Events (SSE)</a><br />
</div>

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
