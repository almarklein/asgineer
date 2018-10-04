import asyncio

import pytest
import websocket

from testutils import URL, PORT, ServerProcess


def make_ws_request(url, messages_to_send=None):
    messages = []
    errors = []
    
    def on_open(ws):
        for m in messages_to_send or []:
            ws.send(m)
    
    def on_message(ws, message):
        messages.append(message)
        if message == 'CLIENT_CLOSE':
            ws.close()  # todo: seem unable to do this *now*
    
    def on_error(ws, error):
        errors.append(error)

    ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error)
    ws.run_forever()
    
    return messages, errors

##


def test_websocket1():
    
    async def handle_ws(request):
        await request.accept()
        await request.send('some text')
        await request.send(b'some bytes')
        await request.send({'some': 'json'})
    
    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace('http', 'ws')))
    
    assert messages == ["some text", b"some bytes", b'{"some": "json"}']
    assert not errors
    assert not p.out
    
    
    async def handle_ws(request):
        await request.accept()
        await request.send('hi')
        await request.send('CLIENT_CLOSE')
        # Wait for client to close connection
        # async for m in request.receive_iter():
        #     print(m)
    
    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace('http', 'ws')))
    
    assert messages == ["hi", "CLIENT_CLOSE"]
    assert not errors
    assert not p.out


def test_websocket2_echo():
    
    async def handle_ws(request):
        await request.accept()
        
        await request.send('some text')
        await request.send(b'some bytes')
        await request.send({'some': 'json'})
    
    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace('http', 'ws')))
    
    assert messages == ["some text", b"some bytes", b'{"some": "json"}']
    assert not errors
    assert not p.out


def test_websocket_no_accept():
    
    async def handle_ws(request):
        await request.send('some text')
        await request.send(b'some bytes')
        await request.send({'some': 'json'})
        
    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace('http', 'ws')))
    
    assert messages == []
    assert errors
    assert "Error in websocket handler" in p.out


def test_websocket_should_return_none():
    
    # Returning a value, even if the rest of the request is ok will
    # make the server log an error.
    
    async def handle_ws(request):
        await request.accept()
        await request.send('some text')
        return 7
        
    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace('http', 'ws')))
    
    assert messages == ['some text']  # the request went fine
    assert not errors  # no errors as ws is concerned
    assert "should return None" in p.out
    
    
    # This is a classic case where a user is doing it wrong, and the error
    # message should (hopefully) help.
    
    async def handle_ws(request):
        return "<html>hi</html>"
        
    with ServerProcess(handle_ws) as p:
        messages, errors = make_ws_request((URL.replace('http', 'ws')))
    
    assert messages == []
    assert errors  # ws errors
    assert "should return None" in p.out


if __name__ == "__main__":
    from testutils import run_tests, set_backend_from_argv

    set_backend_from_argv()
    run_tests(globals())
