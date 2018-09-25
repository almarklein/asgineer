class BaseRequest:
    """ Representation of an HTTP request. An object of this class is
    passed to the request handler.
    """

    __slots__ = (
        "_scope",
        "_receive",
        "_iter_done",
        "_url",
        "_headers",
        "_body",
        "_querylist",
    )

    def __init__(self, scope, receive):
        self._scope = scope
        self._receive = receive
        self._iter_done = False

        self._headers = None
        self._body = None
        self._querylist = None

    @property
    def scope(self):
        """ A dict representing the raw ASGI scope. See the
        [ASGI reference](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope)
        for details.
        """
        return self._scope

    @property
    def method(self):
        """ The HTTP method (string). E.g. 'HEAD', 'GET', 'PUT', 'POST', 'DELETE'.
        """
        return self._scope["method"]

    @property
    def headers(self):
        """ A dictionary representing the headers. Both keys and values are strings.
        """
        if self._headers is None:
            self._headers = dict(
                (key.decode(), val.decode()) for key, val in self._scope["headers"]
            )
        return self._headers

    @property
    def url(self):
        """ The full (unquoted) url, composed of scheme, host, port,
        path, and query parameters (string).
        """
        url = f"{self.scheme}://{self.host}:{self.port}{self.path}"
        if self.querylist:
            url += "?" + "&".join(f"{key}={val}" for key, val in self.querylist)
        return url

    @property
    def scheme(self):
        """ The URL scheme (string). E.g. 'http' or 'https'.
        """
        return self._scope["scheme"]

    @property
    def host(self):
        """ The server's host name (string).
        See also ``scope['server']`` and ``scope['client']``.
        """
        return self._scope["server"][0]

    @property
    def port(self):
        """ The server's port (integer).
        """
        return self._scope["server"][1]

    @property
    def path(self):
        """ The path part of the URL (a string, with percent escapes decoded).
        """
        return (
            self._scope.get("root_path", "") + self._scope["path"]
        )  # is percent-decoded

    @property
    def querylist(self):
        """ A list with (key, value) tuples, representing the URL query parameters.
        """
        if self._querylist is None:
            q = self._scope["query_string"]  # bytes, not percent decoded
            self._querylist = parse_qsl(q.decode())
        return self._querylist

    @property
    def querydict(self):
        """ A dictionary representing the URL query parameters.
        """
        return dict(self.querylist)


class HttpRequest(BaseRequest):
    
    __slots__ = (
        "_receive",
        "_iter_done",
        "_body",
    )

    def __init__(self, scope, receive):
        super().__init__(scope)
        self._receive = receive
        self._iter_done = False
        self._body = None
    
    async def iter_body(self):
        """ An async generator that iterates over the chunks in the body.
        """
        if self._iter_done:
            raise IOError("Request body was already consumed.")
        self._iter_done = True
        while True:
            message = await self._receive()
            if message["type"] == "http.request":
                yield bytes(message.get("body", b""))  # some servers return bytearray
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                raise IOError("Client disconnected")

    async def get_body(self, limit=10 * 2 ** 20):
        """ Coroutine to get the bytes of the body.
        If the end of the stream is not reached before the byte limit
        is reached (default 10MiB), raises an IOError.
        """
        if self._body is None:
            nbytes = 0
            chunks = []
            async for chunk in self.iter_body():
                nbytes += len(chunk)
                if nbytes > limit:
                    chunks.clear()
                    raise IOError("Request body too large")
                chunks.append(chunk)
            self._body = b"".join(chunks)
        return self._body

    async def get_json(self, limit=10 * 2 ** 20):
        """ Coroutine to get the body as a dict.
        If the end of the stream is not reached before the byte limit
        is reached (default 10MiB), raises an IOError.
        """
        body = await self.get_body(limit)
        return json.loads(body.decode())


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


class WebsocketRequest(Request):
    
    __slots__ = (
        "_receive",
        "_send",
        "_iter_done",
        "_client_state",
        "_application_state",
    )

    def __init__(self, scope, receive, send):
        assert scope["type"] == "websocket"
        super().__init__(scope)
        self._receive = receive
        self._send = send
        self._client_state = CONNECTING
        self._application_state = CONNECTING
    
    async def raw_receive(self):
        """
        Receive ASGI websocket messages, ensuring valid state transitions.
        """
        if self._client_state == CONNECTING:
            message = await self._receive()
            message_type = message["type"]
            assert message_type == "websocket.connect"
            self._client_state = CONNECTED
            return message
        elif self._client_state == CONNECTED:
            message = await self._receive()
            message_type = message["type"]
            assert message_type in {"websocket.receive", "websocket.disconnect"}
            if message_type == "websocket.disconnect":
                self._client_state = DISCONNECTED
            return message
        else:
            raise RuntimeError(
                'Cannot call "receive" once a disconnect message has been received.'
            )

    async def raw_send(self, message):
        """
        Send ASGI websocket messages, ensuring valid state transitions.
        """
        if self._application_state == CONNECTING:
            message_type = message["type"]
            assert message_type in {"websocket.accept", "websocket.close"}
            if message_type == "websocket.close":
                self._application_state = DISCONNECTED
            else:
                self._application_state = CONNECTED
            await self._send(message)
        elif self._application_state == CONNECTED:
            message_type = message["type"]
            assert message_type in {"websocket.send", "websocket.close"}
            if message_type == "websocket.close":
                self._application_state = DISCONNECTED
            await self._send(message)
        else:
            raise RuntimeError('Cannot call "send" once a close message has been sent.')

    async def accept(self, subprotocol=None):
        if self._client_state == CONNECTING:
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
        assert self._application_state == CONNECTED, self._application_state
        message = await self.raw_receive()
        self._raise_on_disconnect(message)
        return message["text"]

    async def receive_bytes(self):
        assert self._application_state == CONNECTED
        message = await self.raw_receive()
        self._raise_on_disconnect(message)
        return message["bytes"]

    async def receive_json(self):
        assert self._application_state == CONNECTED
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
