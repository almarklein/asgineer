"""
This module implements the HttpRequest and WebsocketRequest classes that
are passed as an argument into the user's handler function.
"""

import weakref
import json
from urllib.parse import parse_qsl  # urlparse, unquote

from ._compat import sleep, Event, wait_for_any_then_cancel_the_rest


CONNECTING = 0
CONNECTED = 1
DONE = 2
DISCONNECTED = 3


class DisconnectedError(IOError):
    """ An error raised when the connection is disconnected by the client.
    Subclass of IOError. You don't need to catch these - it is considered
    ok for a handler to exit by this.
    """


class BaseRequest:
    """ Base request class, defining the properties to get access to
    the request metadata.
    """

    __slots__ = ("__weakref__", "_scope", "_headers", "_querylist", "_request_sets")

    def __init__(self, scope):
        self._scope = scope
        self._headers = None
        self._querylist = None
        self._request_sets = set()

    async def _destroy(self):
        """ Method to be used internally to perform cleanup.
        """
        for s in self._request_sets:
            try:
                s.discard(self)
            except Exception:  # pragma: no cover
                pass
        self._request_sets.clear()

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

    __slots__ = (
        "_receive",
        "_send",
        "_client_state",
        "_app_state",
        "_body",
        "_wakeup_event",
    )

    def __init__(self, scope, receive, send):
        super().__init__(scope)
        self._receive = receive
        self._send = send
        self._client_state = CONNECTED  # CONNECTED -> DONE -> DISCONNECTED
        self._app_state = CONNECTING  # CONNECTING -> CONNECTED -> DONE
        self._body = None
        self._wakeup_event = None

    async def accept(self, status=200, headers={}):
        """ Accept this http request. Sends the status code and headers.

        In Asgineer, a response can be provided in two ways. The simpler
        (preferred) way is to let the handler return status, headers
        and body. Alternatively, one can use use ``accept()`` and
        ``send()``. In the latter case, the handler must return None.

        Using ``accept()`` and ``send()`` is mostly intended for
        long-lived responses such as chunked data, long polling and
        SSE.

        Note that when using a handler return value, Asgineer
        automatically sets headers based on the body. This is not the
        case when using ``accept``. (Except that the ASGI server will
        set "transfer-encoding" to "chunked" if "content-length" is not
        specified.)
        """
        # Check status
        if self._app_state != CONNECTING:
            raise IOError("Cannot accept an already accepted connection.")
        # Check and convert input
        status = int(status)
        try:
            rawheaders = [(k.encode(), v.encode()) for k, v in headers.items()]
        except Exception:
            raise TypeError("Header keys and values must all be strings.")
        # Send our first message
        self._app_state = CONNECTED
        msg = {"type": "http.response.start", "status": status, "headers": rawheaders}
        await self._send(msg)

    async def _receive_chunk(self):
        """ Receive a chunk of data, returning a bytes object.
        Raises ``DisconnectedError`` when the connection is closed.
        """
        # Check status
        if self._client_state == DISCONNECTED:
            raise IOError("Cannot receive from connection that already disconnected.")
        # Receive
        message = await self._receive()
        mt = "http.disconnect" if message is None else message["type"]
        if mt == "http.request":
            data = bytes(message.get("body", b""))  # some servers return bytearray
            if not message.get("more_body", False):
                self._client_state = DONE
            return data
        elif mt == "http.disconnect":
            self._client_state = DISCONNECTED
            raise DisconnectedError()
        else:  # pragma: no cover
            raise IOError(f"Unexpected message type: {mt}")

    async def send(self, data, more=True):
        """ Send (a chunk of) data, representing the response. Note that
        ``accept()`` must be called first. See ``accept()`` for details.
        """
        # Compose message
        more = bool(more)
        if isinstance(data, str):
            data = data.encode()
        elif not isinstance(data, bytes):
            raise TypeError(f"Can only send bytes/str over http, not {type(data)}.")
        message = {"type": "http.response.body", "body": data, "more_body": more}
        # Send
        if self._app_state == CONNECTED:
            if not more:
                self._app_state = DONE
            await self._send(message)
        elif self._app_state == CONNECTING:
            raise IOError("Cannot send before calling accept.")
        else:
            raise IOError("Cannot send to a closed connection.")

    async def sleep_while_connected(self, seconds):
        """ Async sleep, wake-able, and only while the connection is active.
        Intended for use in long polling and server side events (SSE):

        * Returns after the given amount of seconds.
        * Returns when the request ``wakeup()`` is called.
        * Raises ``DisconnectedError`` when the connection is closed.
        * Note that this drops all received data.
        """
        if self._client_state == DISCONNECTED:
            raise IOError("Cannot wait for connection that already disconnected.")
        if self._wakeup_event is None:
            self._wakeup_event = Event()
        self._wakeup_event.clear()
        await wait_for_any_then_cancel_the_rest(
            sleep(seconds), self._wakeup_event.wait(), self._receive_until_disconnect(),
        )
        if self._client_state == DISCONNECTED:
            raise DisconnectedError()  # see _receive_until_disconnect

    async def _receive_until_disconnect(self):
        """ Keep receiving until the client disconnects.
        """
        while True:
            try:
                await self._receive_chunk()
            except DisconnectedError:
                break  # will re-raise in sleep_while_connected

    async def wakeup(self):
        """ Awake any tasks that are waiting in ``sleep_while_connected()``.
        """
        if self._wakeup_event is not None:
            self._wakeup_event.set()

    async def iter_body(self):
        """ Async generator that iterates over the chunks in the body.
        During iteration you should probably take measures to avoid excessive
        memory usage to prevent server vulnerabilities.
        Raises ``DisconnectedError`` when the connection is closed.
        """
        # Check status
        if self._client_state == DONE:
            raise IOError("Cannot receive an http request that is already consumed.")
        # Iterate
        while True:
            chunk = await self._receive_chunk()
            yield chunk
            if self._client_state != CONNECTED:  # i.e. DONE or DISCONNECTED
                break

    async def get_body(self, limit=10 * 2 ** 20):
        """ Async function to get the bytes of the body.
        If the end of the stream is not reached before the byte limit
        is reached (default 10MiB), raises an ``IOError``.
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
        is reached (default 10MiB), raises an ``IOError``.
        """
        body = await self.get_body(limit)
        return json.loads(body.decode())


class WebsocketRequest(BaseRequest):
    """ Subclass of BaseRequest to represent a websocket request. An
    object of this class is passed to the request handler.
    """

    __slots__ = ("_receive", "_send", "_client_state", "_app_state")

    def __init__(self, scope, receive, send):
        assert scope["type"] == "websocket", f"Unexpected ws scope type {scope['type']}"
        super().__init__(scope)
        self._receive = receive
        self._send = send
        self._client_state = CONNECTING  # CONNECTING -> CONNECTED -> DISCONNECTED
        self._app_state = CONNECTING  # CONNECTING -> CONNECTED -> DISCONNECTED

    async def accept(self, subprotocol=None):
        """ Async function to accept the websocket connection.
        This needs to be called before any sending or receiving.
        Raises ``DisconnectedError`` when the client closed the connection.
        """
        # If we haven't yet seen the 'connect' message, then wait for it first.
        if self._client_state == CONNECTING:
            message = await self._receive()
            mt = message["type"]
            if mt == "websocket.connect":
                self._client_state = CONNECTED
            elif mt == "websocket.disconnect":
                self._client_state = DISCONNECTED
                raise DisconnectedError()
            else:  # pragma: no cover
                raise IOError(f"Unexpected ws message type {mt}")
        elif self._client_state == DISCONNECTED:
            raise IOError("Cannot accept ws that already disconnected.")
        # Accept from our side
        if self._app_state == CONNECTING:
            await self._send({"type": "websocket.accept", "subprotocol": subprotocol})
            self._app_state = CONNECTED
        else:
            raise IOError("Cannot accept an already accepted ws connection.")

    async def send(self, data):
        """ Async function to send a websocket message. The value can
        be ``bytes``, ``str`` or ``dict``. In the latter case, the message is
        encoded with JSON (and UTF-8).
        """
        # Compose message
        if isinstance(data, bytes):
            message = {"type": "websocket.send", "bytes": data}
        elif isinstance(data, str):
            message = {"type": "websocket.send", "text": data}
        elif isinstance(data, dict):
            encoded = json.dumps(data).encode()
            message = {"type": "websocket.send", "bytes": encoded}
        else:
            raise TypeError(f"Can only send bytes/str/dict over ws, not {type(data)}")
        # Send it. In contrast to http, we cannot send after the client closed.
        if self._client_state == DISCONNECTED:
            raise IOError("Cannot send to a disconnected ws.")
        elif self._app_state == CONNECTED:
            await self._send(message)
        elif self._app_state == CONNECTING:
            raise IOError("Cannot send before calling accept on ws.")
        else:
            raise IOError("Cannot send to a closed ws.")

    async def receive(self):
        """ Async function to receive one websocket message. The result can be
        ``bytes`` or ``str`` (depending on how it was sent).
        Raises ``DisconnectedError`` when the client closed the connection.
        """
        # Get it
        if self._client_state == CONNECTED:
            message = await self._receive()
        elif self._client_state == DISCONNECTED:
            raise IOError("Cannot receive from ws that already disconnected.")
        else:
            raise IOError("Cannot receive before calling accept on ws.")
        # Process
        mt = message["type"]
        if mt == "websocket.receive":
            return message.get("bytes", None) or message.get("text", None) or b""
        elif mt == "websocket.disconnect":
            self._client_state = DISCONNECTED
            raise DisconnectedError(f"ws disconnect {message.get('code', 1000)}")
        else:  # pragma: no cover
            raise IOError(f"Unexpected ws message type {mt}")

    async def receive_iter(self):
        """ Async generator to iterate over incoming messages as long
        as the connection is not closed. Each message can be a ``bytes`` or ``str``.
        """
        while True:
            try:
                result = await self.receive()
                yield result
            except DisconnectedError:
                break

    async def receive_json(self):
        """ Async convenience function to receive a JSON message. Works
        on binary as well as text messages, as long as its JSON encoded.
        Raises ``DisconnectedError`` when the client closed the connection.
        """
        result = await self.receive()
        if isinstance(result, bytes):
            result = result.decode()
        return json.loads(result)

    async def close(self, code=1000):
        """ Async function to close the websocket connection.
        """
        await self._send({"type": "websocket.close", "code": code})
        self._app_state = DISCONNECTED


class RequestSet:
    """ A set of request objects that are currenlty active.

    This class can help manage long-lived connections such as with long
    polling, SSE or websockets. All requests in as set can easily be
    awoken at once, and requests are automatically removed from the set
    when they're done.
    """

    def __init__(self):
        self._s = weakref.WeakSet()

    def __len__(self):
        return len(self._s)

    def __iter__(self):
        return iter(self._s)

    def add(self, request):
        """ Add a request object to the set.
        """
        if not isinstance(request, BaseRequest):
            raise TypeError("RequestSet can only contain request objects.")
        request._request_sets.add(self)
        self._s.add(request)

    def discard(self, request):
        """ Remove the given request object from the set.
        If not present, it is ignored.
        """
        self._s.discard(request)

    def clear(self):
        """ Remove all request objects from the set.
        """
        self._s.clear()
