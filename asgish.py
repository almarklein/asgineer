"""
asgish - An ASGI web framework with an ASGI-ish API
"""

import json
import inspect
from urllib.parse import parse_qsl  # urlparse, unquote


def handler2asgi(handler):
    """ Convert a request handler (a coroutine function) to an ASGI
    application, which can be served with an ASGI server, such as
    Uvicorn, Hypercorn, Daphne, etc.
    """

    if not inspect.iscoroutinefunction(handler):
        raise TypeError("Handler function must be a coroutine function.")

    class Application(BaseApplication):
        _handler = staticmethod(handler)

    return Application


class BaseApplication:
    """ Base ASGI application class.
    """

    _handler = None

    def __init__(self, scope):
        self._scope = scope

    async def __call__(self, receive, send):
        request = Request(self._scope, receive)

        # === Call handler to get the result
        try:

            result = await self._handler(request)

        except Exception as err:
            # Error in the handler
            errer_text = "Error in request handler: " + str(err)
            await send({"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": errer_text.encode()})
            raise err

        # === Process the handler output
        try:

            # Get status, headers and body from the result
            if isinstance(result, tuple):
                if len(result) == 3:
                    status, headers, body = result
                elif len(result) == 2 and isinstance(result[0], (set, dict)):
                    # Also go this path on set to get a better error below
                    status = 200
                    headers, body = result
                elif len(result) == 2:
                    headers = {}
                    status, body = result
                elif len(result) == 1:
                    status, headers, body = 200, {}, result[0]
                else:
                    raise ValueError(f"Handler returned {len(result)}-tuple.")
            else:
                status, headers, body = 200, {}, result

            # Validate status and headers
            assert isinstance(
                status, int
            ), f"Status code must be an int, not {type(status)}"
            assert isinstance(
                headers, dict
            ), f"Headers must be a dict, not {type(headers)}"

            # Convert the body
            if isinstance(body, bytes):
                pass
            elif isinstance(body, str):
                if body.startswith(("<!DOCTYPE ", "<html>")):
                    headers.setdefault("content-type", "text/html")
                else:
                    headers.setdefault("content-type", "text/plain")
                body = body.encode()
            elif isinstance(body, dict):
                try:
                    body = json.dumps(body).encode()
                except Exception as err:
                    raise ValueError(f"Could not JSON encode body: {err}")
                headers.setdefault("content-type", "application/json")
            elif inspect.isasyncgen(body):
                pass
            else:
                if inspect.isgenerator(body):
                    raise ValueError(
                        f"Body cannot be a regular generator, use an async generator."
                    )
                else:
                    raise ValueError(f"Body cannot be {type(body)}.")

            # Convert and further validate headers
            if isinstance(body, bytes):
                headers.setdefault("content-length", str(len(body)))
            try:
                rawheaders = [(k.encode(), v.encode()) for k, v in headers.items()]
            except Exception:
                raise ValueError("Header keys and values must all be strings.")

        except Exception as err:
            # Error in hanlding handler output
            errer_text = "Error in processing handler output: " + str(err)
            await send({"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": errer_text.encode()})
            raise err

        # === Send response
        start = {"type": "http.response.start", "status": status, "headers": rawheaders}
        if isinstance(body, bytes):
            # The easy way; body as one message, not much error catching we can do here.
            await send(start)
            if isinstance(body, bytes):
                await send({"type": "http.response.body", "body": body})
        else:
            # Chunked response, stuff can go wrong in the middle
            start_is_sent = False
            try:
                async for chunk in body:
                    if isinstance(chunk, str):
                        chunk = chunk.encode()
                    assert isinstance(
                        chunk, bytes
                    ), f"Body chunk must be str or bytes, not {type(chunk)}"
                    if not start_is_sent:
                        start_is_sent = True
                        await send(start)
                    await send(
                        {"type": "http.response.body", "body": chunk, "more_body": True}
                    )
                await send(
                    {"type": "http.response.body", "body": b"", "more_body": False}
                )

            except Exception as err:
                if not start_is_sent:
                    errer_text = "Error in chunked response: " + str(err)
                    await send(
                        {"type": "http.response.start", "status": 500, "headers": []}
                    )
                    await send(
                        {"type": "http.response.body", "body": errer_text.encode()}
                    )
                else:  # end-of-body has also not been send
                    await send(
                        {"type": "http.response.body", "body": b"", "more_body": False}
                    )
                raise err


class Request:
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
