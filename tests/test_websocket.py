import sys
import asyncio

from autobahn.asyncio.websocket import WebSocketClientProtocol, WebSocketClientFactory

from testutils import URL, ServerProcess


def make_ws_request(url, messages_to_send=None):

    host, port = url.split("//")[-1].split(":")
    port = int(port)

    messages = []
    errors = []

    class MyClientProtocol(WebSocketClientProtocol):
        def sendCloseLater(self):
            loop = asyncio.get_event_loop()
            loop.call_later(1.0, self.sendClose)

        def onOpen(self):
            for m in messages_to_send or []:
                if m is None:
                    self.sendCloseLater()
                elif isinstance(m, str):
                    self.sendMessage(m.encode(), False)
                else:
                    self.sendMessage(m, True)

        def onMessage(self, message, isBinary):
            if not isBinary:
                message = message.decode()
            messages.append(message)
            if message == "CLIENT_CLOSE":
                self.sendCloseLater()

        def onClose(self, wasClean, code, reason):
            loop = asyncio.get_event_loop()
            loop.stop()

        def dropConnection(self, abort=False):
            if abort and not self.wasClean:
                errors.append(self.wasNotCleanReason)
            super().dropConnection(abort)

    factory = WebSocketClientFactory(url)
    factory.protocol = MyClientProtocol

    loop = asyncio.get_event_loop()
    coro = loop.create_connection(factory, host, port)
    loop.run_until_complete(coro)
    loop.run_forever()

    return messages, errors


##


def test_websocket1():

    # Send messages from server to client

    async def handle_ws(request):
        await request.accept()
        await request.send("some text")
        await request.send(b"some bytes")
        await request.send({"some": "json"})

    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace("http", "ws")))

    assert messages == ["some text", b"some bytes", b'{"some": "json"}']
    assert not errors
    assert not p.out

    # Send messages from server to client, let the client stop

    async def handle_ws(request):
        await request.accept()
        await request.send("hi")
        await request.send("CLIENT_CLOSE")
        # Wait for client to close connection
        async for m in request.receive_iter():
            print(m)

    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace("http", "ws")))

    assert messages == ["hi", "CLIENT_CLOSE"]
    assert not errors
    assert not p.out


def test_websocket2():

    # Send messages from client to server

    async def handle_ws(request):
        await request.accept()
        async for m in request.receive_iter():
            print(m)
        sys.stdout.flush()

    send = "hi", "there", None  # None means client closes

    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace("http", "ws")), send)

    assert messages == []
    assert not errors
    assert p.out == "hi\nthere"

    # Send messages from server to client, let the server stop

    async def handle_ws(request):
        await request.accept()
        async for m in request.receive_iter():
            print(m)
            if m == "SERVER_STOP":
                break
        sys.stdout.flush()

    send = "hi", "there", "SERVER_STOP"

    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace("http", "ws")), send)

    assert messages == []
    assert not errors
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

    send = "hi", "there", "SERVER_STOP"

    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace("http", "ws")), send)

    assert messages == ["hi", "there"]
    assert not errors
    assert not p.out


def test_websocket_no_accept():
    async def handle_ws(request):
        await request.send("some text")
        await request.send(b"some bytes")
        await request.send({"some": "json"})

    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace("http", "ws")))

    assert messages == []
    assert errors
    assert "Error in websocket handler" in p.out


def test_websocket_should_return_none():

    # Returning a value, even if the rest of the request is ok will
    # make the server log an error.

    async def handle_ws(request):
        await request.accept()
        await request.send("some text")
        return 7

    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace("http", "ws")))

    assert messages == ["some text"]  # the request went fine
    assert not errors  # no errors as ws is concerned
    assert "should return None" in p.out

    # This is a classic case where a user is doing it wrong, and the error
    # message should (hopefully) help.

    async def handle_ws(request):
        return "<html>hi</html>"

    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace("http", "ws")))

    assert messages == []
    assert errors  # ws errors
    assert "should return None" in p.out


if __name__ == "__main__":
    from testutils import run_tests, set_backend_from_argv

    set_backend_from_argv()
    run_tests(globals())
