"""
Test behavior for websocket handlers.
"""

import sys

from common import make_server


def test_websocket1():

    # Send messages from server to client

    async def handle_ws(request):
        await request.accept()
        await request.send("some text")
        await request.send(b"some bytes")
        await request.send({"some": "json"})
        await request.close()

    async def client(ws):
        messages = []
        async for m in ws:
            messages.append(m)
        return messages

    with make_server(handle_ws) as p:
        messages = p.ws_communicate("/", client)

    assert messages == ["some text", b"some bytes", b'{"some": "json"}']
    assert not p.out

    # Send messages from server to client, let the client stop

    async def handle_ws(request):
        await request.accept()
        await request.send("hi")
        await request.send("CLIENT_CLOSE")
        # Wait for client to close connection
        async for m in request.receive_iter():
            print(m)

    async def client(ws):
        messages = []
        async for m in ws:
            messages.append(m)
            if m == "CLIENT_CLOSE":
                break
        return messages

    with make_server(handle_ws) as p:
        messages = p.ws_communicate("/", client)

    assert messages == ["hi", "CLIENT_CLOSE"]
    assert not p.out


def test_websocket2():

    # Send messages from client to server

    async def handle_ws(request):
        await request.accept()
        async for m in request.receive_iter():
            print(m)
        sys.stdout.flush()

    async def client(ws):
        messages = []
        await ws.send("hi")
        await ws.send("there")
        await ws.close()
        async for m in ws:
            messages.append(m)
            if m == "CLIENT_CLOSE":
                break
        return messages

    with make_server(handle_ws) as p:
        messages = p.ws_communicate("/", client)

    assert messages == []
    assert p.out == "hi\nthere"

    # Send messages from server to client, let the server stop

    async def handle_ws(request):
        await request.accept()
        async for m in request.receive_iter():
            print(m)
            if m == "SERVER_STOP":
                break
        sys.stdout.flush()

    async def client(ws):
        messages = []
        await ws.send("hi")
        await ws.send("there")
        await ws.send("SERVER_STOP")
        async for m in ws:
            messages.append(m)
            if m == "CLIENT_CLOSE":
                break
        return messages

    with make_server(handle_ws) as p:
        messages = p.ws_communicate("/", client)

    assert messages == []
    assert p.out == "hi\nthere\nSERVER_STOP"


def test_websocket_echo():
    async def handle_ws(request):
        await request.accept()
        async for m in request.receive_iter():
            if m == "SERVER_STOP":
                break
            else:
                await request.send(m)
        sys.stdout.flush()

    async def client(ws):
        messages = []
        await ws.send("hi")
        await ws.send("there")
        await ws.send("SERVER_STOP")
        async for m in ws:
            messages.append(m)
            if m == "CLIENT_CLOSE":
                break
        return messages

    with make_server(handle_ws) as p:
        messages = p.ws_communicate("/", client)

    assert messages == ["hi", "there"]
    assert not p.out


def test_websocket_receive():
    async def handle_ws(request):
        await request.accept()
        print(await request.receive_json())
        print(await request.receive_json())
        sys.stdout.flush()

    async def client(ws):
        await ws.send('{"foo": 3}')
        await ws.send(b'{"bar": 3}')

    with make_server(handle_ws) as p:
        p.ws_communicate("/", client)

    assert p.out == "{'foo': 3}\n{'bar': 3}"


def test_websocket_receive_too_much():
    async def handle_ws1(request):
        await request.accept()
        async for m in request.receive_iter():
            print(m)
        sys.stdout.flush()

    async def handle_ws2(request):
        await request.accept()
        print(await request.receive())
        print(await request.receive())
        sys.stdout.flush()

    async def client(ws):
        await ws.send("hellow")
        # await ws.close()  # this would be the nice behavior

    with make_server(handle_ws1) as p:
        p.ws_communicate("/", client)

    assert "hellow" == p.out.strip()

    with make_server(handle_ws2) as p:
        p.ws_communicate("/", client)

    assert "hellow" in p.out
    assert "EOFError" in p.out and "websocket disconnect" in p.out.lower()
    assert "KeyError" not in p.out


def test_websocket_send_invalid_data():
    async def handle_ws(request):
        await request.accept()
        await request.send(4)

    async def client(ws):
        await ws.send("hellow")

    with make_server(handle_ws) as p:
        p.ws_communicate("/", client)

    assert "TypeError" in p.out


def test_websocket_no_accept():
    async def handle_ws(request):
        await request.send("some text")
        await request.send(b"some bytes")
        await request.send({"some": "json"})

    async def client(ws):
        messages = []
        async for m in ws:
            messages.append(m)
            if m == "CLIENT_CLOSE":
                break
        return messages

    with make_server(handle_ws) as p:
        messages = p.ws_communicate("/", client)

    assert messages == [] or messages is None  # handshake fails
    assert "Error in websocket handler" in p.out


def test_websocket_should_return_none():

    # Returning a value, even if the rest of the request is ok will
    # make the server log an error.

    async def handle_ws(request):
        await request.accept()
        await request.send("some text")
        return 7

    async def client(ws):
        messages = []
        async for m in ws:
            messages.append(m)
            if m == "CLIENT_CLOSE":
                break
        return messages

    with make_server(handle_ws) as p:
        messages = p.ws_communicate("/", client)

    assert messages == ["some text"]  # the request went fine
    assert "should return None" in p.out

    # This is a classic case where a user is doing it wrong, and the error
    # message should (hopefully) help.

    async def handle_ws(request):
        return "<html>hi</html>"

    async def client(ws):
        messages = []
        async for m in ws:
            messages.append(m)
            if m == "CLIENT_CLOSE":
                break
        return messages

    with make_server(handle_ws) as p:
        messages = p.ws_communicate("/", client)

    assert messages == [] or messages is None  # handshake fails
    assert "should return None" in p.out


if __name__ == "__main__":
    from common import run_tests, set_backend_from_argv

    set_backend_from_argv()
    run_tests(globals())
