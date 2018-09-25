import json

from asgish import Request


CONNECTING = 0
CONNECTED = 1
DISCONNECTED = 2


class WebSocketDisconnect(Exception):
    def __init__(self, code=1000):
        self.code = code



class WebSocketClose:
    def __init__(self, code=1000):
        self.code = code

    async def __call__(self, receive, send):
        await send({"type": "websocket.close", "code": self.code})


class WebSocket(Request):
    
    def __init__(self, scope, receive, send):
        assert scope["type"] == "websocket"
        super().__init__(scope, receive)
        self._send = send
        self.client_state = CONNECTING
        self.application_state = CONNECTING
    
    # def __del__(self):
    #     try:
    #         self.close()
    #     except Exception:
    #         pass
    
    async def raw_receive(self):
        """
        Receive ASGI websocket messages, ensuring valid state transitions.
        """
        if self.client_state == CONNECTING:
            message = await self._receive()
            message_type = message["type"]
            assert message_type == "websocket.connect"
            self.client_state = CONNECTED
            return message
        elif self.client_state == CONNECTED:
            message = await self._receive()
            message_type = message["type"]
            assert message_type in {"websocket.receive", "websocket.disconnect"}
            if message_type == "websocket.disconnect":
                self.client_state = DISCONNECTED
            return message
        else:
            raise RuntimeError(
                'Cannot call "receive" once a disconnect message has been received.'
            )

    async def raw_send(self, message):
        """
        Send ASGI websocket messages, ensuring valid state transitions.
        """
        if self.application_state == CONNECTING:
            message_type = message["type"]
            assert message_type in {"websocket.accept", "websocket.close"}
            if message_type == "websocket.close":
                self.application_state = DISCONNECTED
            else:
                self.application_state = CONNECTED
            await self._send(message)
        elif self.application_state == CONNECTED:
            message_type = message["type"]
            assert message_type in {"websocket.send", "websocket.close"}
            if message_type == "websocket.close":
                self.application_state = DISCONNECTED
            await self._send(message)
        else:
            raise RuntimeError('Cannot call "send" once a close message has been sent.')

    async def accept(self, subprotocol=None):
        if self.client_state == CONNECTING:
            # If we haven't yet seen the 'connect' message, then wait for it first.
            await self.raw_receive()
        await self.raw_send({"type": "websocket.accept", "subprotocol": subprotocol})

    def _raise_on_disconnect(self, message):
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message["code"])
    
    async def receive_iter(self):
        while True:
            message = await self.raw_receive()
            if message["type"] == "websocket.disconnect":
                return
            yield message['bytes']
    
    async def receive_text(self):
        assert self.application_state == CONNECTED, self.application_state
        message = await self.raw_receive()
        self._raise_on_disconnect(message)
        return message["text"]

    async def receive_bytes(self):
        assert self.application_state == CONNECTED
        message = await self.raw_receive()
        self._raise_on_disconnect(message)
        return message["bytes"]

    async def receive_json(self):
        assert self.application_state == CONNECTED
        message = await self.raw_receive()
        self._raise_on_disconnect(message)
        encoded = message["bytes"]
        return json.loads(encoded.decode())

    async def send(self, value):
        if isinstance(value, bytes):
            await self.raw_send({"type": "websocket.send", "bytes": value})
        elif isinstance(value, str):
            await self.raw_send({"type": "websocket.send", "text": value})
        elif isinstance(value, dict):
            encoded = json.dumps(value).encode()
            await self.raw_send({"type": "websocket.send", "bytes": encoded})
        else:
            raise TypeError('Can only send bytes/str/dict.')
            
    async def send_text(self, data):
        await self.raw_send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data):
        await self.raw_send({"type": "websocket.send", "bytes": data})

    async def send_json(self, data):
        encoded = json.dumps(data).encode("utf-8")
        await self.raw_send({"type": "websocket.send", "bytes": encoded})

    async def close(self, code=1000):
        await self.raw_send({"type": "websocket.close", "code": code})
