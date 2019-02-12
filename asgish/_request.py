"""
This module implements the HttpRequest and WebsocketRequest classes that
are passed as an argument into the user's handler function.
"""

import json
from urllib.parse import parse_qsl  # urlparse, unquote


class BaseRequest:
    """ Base request class.
    """

    __slots__ = ("_scope", "_headers", "_querylist")

    def __init__(self, scope):
        self._scope = scope
        self._headers = None
        self._querylist = None

    @property
    def scope(self):
        """ A dict representing the raw ASGI scope. See the
        `ASGI reference <https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope>`_
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
        """ A dictionary representing the headers. Both keys and values are
        lowercase strings.
        """
        # We can assume the headers to be made lowercase by h11/httptools/etc. right?
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
        """ he requested host name, taken from the Host header,
        or ``scope['server'][0]`` if there is not Host header.
        See also ``scope['server']`` and ``scope['client']``.
        """
        return self.headers.get("host", self._scope["server"][0]).split(":")[0]

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
        """ A list with ``(key, value)`` tuples, representing the URL query parameters.
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
    """ Subclass of BaseRequest to represent an HTTP request. An object
    of this class is passed to the request handler.
    """

    __slots__ = ("_receive", "_iter_done", "_body")

    def __init__(self, scope, receive):
        super().__init__(scope)
        self._receive = receive
        self._iter_done = False
        self._body = None

    async def iter_body(self):
        """ Async generator that iterates over the chunks in the body.
        During iteration you should probably take measures to avoid excessive
        memory usage to prevent server vulnerabilities.
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
            elif message["type"] == "http.disconnect":  # pragma: no cover
                raise IOError("Client disconnected.")

    async def get_body(self, limit=10 * 2 ** 20):
        """ Async function to get the bytes of the body.
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
                    raise IOError("Request body too large.")
                chunks.append(chunk)
            self._body = b"".join(chunks)
        return self._body

    async def get_json(self, limit=10 * 2 ** 20):
        """ Async function to get the body as a dict.
        If the end of the stream is not reached before the byte limit
        is reached (default 10MiB), raises an IOError.
        """
        body = await self.get_body(limit)
        return json.loads(body.decode())


CONNECTING = 0
CONNECTED = 1
DISCONNECTED = 2


class WebsocketRequest(BaseRequest):
    """ Subclass of BaseRequest to represent a websocket request. An
    object of this class is passed to the request handler.
    """

    __slots__ = ("_receive", "_send", "_client_state", "_application_state")

    def __init__(self, scope, receive, send):
        assert scope["type"] == "websocket", f"Unexpected ws scope type {scope['type']}"
        super().__init__(scope)
        self._receive = receive
        self._send = send
        self._client_state = CONNECTING
        self._application_state = CONNECTING

    async def raw_receive(self):
        """ Async function to receive an ASGI websocket message,
        ensuring valid state transitions.
        """
        if self._client_state == CONNECTING:
            message = await self._receive()
            mt = message["type"]
            assert mt == "websocket.connect", f"Unexpected ws message type {mt}"
            self._client_state = CONNECTED
            return message
        elif self._client_state == CONNECTED:
            message = await self._receive()
            mt = message["type"]
            ok_types = {"websocket.receive", "websocket.disconnect"}
            assert mt in ok_types, f"Unexpected ws message type {mt}"
            if mt == "websocket.disconnect":
                self._client_state = DISCONNECTED
            return message
        else:  # pragma: no cover
            raise IOError(
                'Cannot call "receive" once a client disconnect message has been received.'
            )

    async def raw_send(self, message):
        """ Async function tp send a ASGI websocket message,
        ensuring valid state transitions.
        """
        if self._application_state == CONNECTING:
            mt = message["type"]
            ok_types = {"websocket.accept", "websocket.close"}
            assert mt in ok_types, f"Unexpected ws message type {mt}"
            if mt == "websocket.close":
                self._application_state = DISCONNECTED
            else:
                self._application_state = CONNECTED
            await self._send(message)
        elif self._application_state == CONNECTED:
            mt = message["type"]
            ok_types = {"websocket.send", "websocket.close"}
            assert mt in ok_types, f"Unexpected ws message type {mt}"
            if mt == "websocket.close":
                self._application_state = DISCONNECTED
            await self._send(message)
        else:
            raise IOError('Cannot call "send" once a close message has been sent.')

    async def accept(self, subprotocol=None):
        """ Async function to accept the websocket connection.
        This needs to be called before any sending or receiving.
        """
        if self._client_state == CONNECTING:
            # If we haven't yet seen the 'connect' message, then wait for it first.
            await self.raw_receive()
        await self.raw_send({"type": "websocket.accept", "subprotocol": subprotocol})

    async def receive_iter(self):
        """ Async generator to iterate over incoming messaged as long
        as the connection is not closed. Each message can be a ``bytes`` or ``str``.
        """
        assert self._application_state == CONNECTED, self._application_state
        while True:
            message = await self.raw_receive()
            if message["type"] == "websocket.disconnect":
                return
            # ASGI specifies that either bytes or text is present
            yield message.get("bytes", None) or message.get("text", None) or b""

    async def receive(self):
        """ Async function to receive one websocket message. The result can be
        ``bytes`` or ``str``. Raises ``EOFError`` when a disconnect-message is received.
        """
        assert self._application_state == CONNECTED, self._application_state
        message = await self.raw_receive()
        if message["type"] == "websocket.disconnect":
            raise EOFError("Websocket disconnect", message.get("code", 1000))
        return message.get("bytes", None) or message.get("text", None) or b""

    # todo: maybe receive_bytes and/or receive_text?

    async def receive_json(self):
        """ Async convenience function to receive a JSON message. Works
        on binary as well as text messages, as long as its JSON encoded.
        """
        message = await self.receive()
        if isinstance(message, bytes):
            message = message.decode()
        return json.loads(message)

    async def send(self, value):
        """ Async function to send a websocket message. The value can
        be ``bytes``, ``str`` or ``dict``. In the latter case, the message is
        encoded with JSON (and UTF-8).
        """
        if isinstance(value, bytes):
            await self.raw_send({"type": "websocket.send", "bytes": value})
        elif isinstance(value, str):
            await self.raw_send({"type": "websocket.send", "text": value})
        elif isinstance(value, dict):
            encoded = json.dumps(value).encode()
            await self.raw_send({"type": "websocket.send", "bytes": encoded})
        else:
            raise TypeError("Can only send bytes/str/dict.")

    async def close(self, code=1000):
        """ Async function to close the websocket connection.
        """
        await self.raw_send({"type": "websocket.close", "code": code})
