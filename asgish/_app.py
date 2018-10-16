"""
This module implements an ASGI application class that forms the adapter
between the user-defined handler function and the ASGI server.
"""

import json
import sys
import logging
import inspect
from ._request import HttpRequest, WebsocketRequest

# Initialize the logger to write errors to stderr (but can be overriden)
logger = logging.getLogger("asgish")
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.propagate = False
logger.setLevel(logging.INFO)  # we actually only emit error messages atm


def to_asgi(handler):
    """ Convert a request handler (a coroutine function) to an ASGI
    application, which can be served with an ASGI server, such as
    Uvicorn, Hypercorn, Daphne, etc.
    """

    if not inspect.iscoroutinefunction(handler):
        raise TypeError(
            "asgish.to_asgi() handler function must be a coroutine function."
        )

    class Application(BaseApplication):
        _handler = staticmethod(handler)

    Application.__module__ = handler.__module__
    Application.__name__ = handler.__name__
    return Application


class BaseApplication:
    """ Base ASGI application class.
    """

    _handler = None

    def __init__(self, scope):
        self._scope = scope

    def _error(self, msg):
        """ Log an error message. We don't rely on the server to print
        exceptions, since e.g. Daphne swallows them.
        """
        logger.error(msg)

    async def __call__(self, receive, send):

        if self._scope["type"] == "http":
            request = HttpRequest(self._scope, receive)
            await self._handle_http(request, receive, send)
        elif self._scope["type"] == "websocket":
            request = WebsocketRequest(self._scope, receive, send)
            await self._handle_websocket(request, receive, send)
        elif self._scope["type"] == "lifespan":
            await self._handle_lifespan(receive, send)
        else:
            self._error(f"Dont know about ASGI type {self._scope['type']}")

    async def _handle_lifespan(self, receive, send):
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                # Could do startup stuff here
                logger.info(f"Server is running")
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.cleanup":
                # Could do cleanup stuff here
                logger.info(f"Server is shutting down")
                await send({"type": "lifespan.cleanup.complete"})
                return
            else:
                self._error(f"Unexpected lifespan message {message['type']}")

    async def _handle_websocket(self, request, receive, send):

        # === Call websocket handler
        try:

            result = await self._handler(request)

        except Exception as err:
            # Error in the handler
            error_text = "Error in websocket handler: " + str(err)
            self._error(error_text)
            return
        finally:
            # The ASGI spec specifies that ASGI servers should close
            # the ws connection when the task ends. At the time of
            # writing (04-10-2018), only Uvicorn does this.
            # TODO: Remove this once all servers behave correctly
            try:
                await request.close()
            except Exception:
                pass

        # === Process the handler output
        if result is not None:
            # It's likely that the user is misunderstanding how ws handlers work.
            # Let's be strict and give directions.
            error_text = (
                "A websocket handler should return None; "
                + "use request.send() and request.receive() to communicate."
            )
            self._error(error_text)

    async def _handle_http(self, request, receive, send):

        # === Call request handler to get the result
        try:

            result = await self._handler(request)

        except Exception as err:
            # Error in the handler
            error_text = "Error in request handler: " + str(err)
            self._error(error_text)
            await send({"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": error_text.encode()})
            return

        # === Process the handler output
        try:

            # Get status, headers and body from the result
            if isinstance(result, tuple):
                if len(result) == 3:
                    status, headers, body = result
                elif len(result) == 2:
                    status = 200
                    headers, body = result
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
                if body.startswith(("<!DOCTYPE html>", "<html>")):
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
            error_text = "Error in processing handler output: " + str(err)
            self._error(error_text)
            await send({"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": error_text.encode()})
            return

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
                error_text = "Error in chunked response: " + str(err)
                self._error(error_text)
                if not start_is_sent:
                    await send(
                        {"type": "http.response.start", "status": 500, "headers": []}
                    )
                    await send(
                        {"type": "http.response.body", "body": error_text.encode()}
                    )
                else:  # end-of-body has not been send
                    await send(
                        {"type": "http.response.body", "body": b"", "more_body": False}
                    )
                return
