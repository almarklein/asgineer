"""
This module implements an ASGI application class that forms the adapter
between the user-defined handler function and the ASGI server.
"""

import sys
import json
import logging
import inspect
from ._request import HttpRequest, WebsocketRequest


# Initialize the logger
logger = logging.getLogger("asgineer")
logger.propagate = False
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(
    logging.Formatter(
        fmt="[%(levelname)s %(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)
logger.addHandler(_handler)


def to_asgi(handler):
    """ Convert a request handler (a coroutine function) to an ASGI
    application, which can be served with an ASGI server, such as
    Uvicorn, Hypercorn, Daphne, etc.
    """

    if not inspect.iscoroutinefunction(handler):
        raise TypeError(
            "asgineer.to_asgi() handler function must be a coroutine function."
        )

    class Application(BaseApplication):
        _handler = staticmethod(handler)

    Application.__module__ = handler.__module__
    Application.__name__ = handler.__name__
    return Application


def normalize_response(response):
    """ Normalize the given response, by always returning a 3-element tuple
    (status, headers, body). The body is not "resolved"; it is safe
    to call this function multiple times on the same response.
    """
    # Get status, headers and body from the response
    if isinstance(response, tuple):
        if len(response) == 3:
            status, headers, body = response
        elif len(response) == 2:
            status = 200
            headers, body = response
        elif len(response) == 1:
            status, headers, body = 200, {}, response[0]
        else:
            raise ValueError(f"Handler returned {len(response)}-tuple.")
    else:
        status, headers, body = 200, {}, response

    # Validate status and headers
    if not isinstance(status, int):
        raise ValueError(f"Status code must be an int, not {type(status)}")
    if not isinstance(headers, dict):
        raise ValueError(f"Headers must be a dict, not {type(headers)}")

    return status, headers, body


def guess_content_type_from_body(body):
    """ Guess the content-type based of the body.
    
    * "text/html" for str bodies starting with ``<!DOCTYPE html>`` or ``<html>``.
    * "text/plain" for other str bodies.
    * "application/json" for dict bodies.
    * "application/octet-stream" otherwise.
    """
    if isinstance(body, str):
        if body.startswith(("<!DOCTYPE html>", "<!doctype html>", "<html>")):
            return "text/html"
        else:
            return "text/plain"
    elif isinstance(body, dict):
        return "application/json"
    else:
        return "application/octet-stream"


class BaseApplication:
    """ Base ASGI application class.
    """

    _handler = None

    def __init__(self, scope):
        self._scope = scope

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
            logger.warn(f"Unknown ASGI type {self._scope['type']}")

    async def _handle_lifespan(self, receive, send):
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                # Could do startup stuff here
                try:
                    logger.info("Server is starting up")
                except Exception:  # pragma: no cover
                    pass
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                # Could do shutdown stuff here
                try:
                    logger.info("Server is shutting down")
                except Exception:  # pragma: no cover
                    pass
                await send({"type": "lifespan.shutdown.complete"})
                return
            else:
                logger.warn(f"Unknown lifespan message {message['type']}")

    async def _handle_websocket(self, request, receive, send):

        # === Call websocket handler
        try:

            result = await self._handler(request)

        except Exception as err:
            # Error in the handler
            error_text = f"{type(err).__name__} in websocket handler: {str(err)}"
            logger.error(error_text, exc_info=err)
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
            logger.error(error_text)

    async def _handle_http(self, request, receive, send):

        # === Call request handler to get the result
        try:

            result = await self._handler(request)

        except Exception as err:
            # Error in the handler
            error_text = f"{type(err).__name__} in request handler: {str(err)}"
            logger.error(error_text, exc_info=err)
            await send({"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": error_text.encode()})
            return

        # === Process the handler output
        try:

            status, headers, body = normalize_response(result)

            # Make sure that there is a content type
            if "content-type" not in headers:
                headers["content-type"] = guess_content_type_from_body(body)

            # Convert the body
            if isinstance(body, bytes):
                pass
            elif isinstance(body, str):
                body = body.encode()
            elif isinstance(body, dict):
                try:
                    body = json.dumps(body).encode()
                except Exception as err:
                    raise ValueError(f"Could not JSON encode body: {err}")
            elif inspect.isasyncgen(body):
                pass
            else:
                if inspect.isgenerator(body):
                    raise ValueError(
                        f"Body cannot be a regular generator, use an async generator."
                    )
                elif inspect.iscoroutine(body):
                    raise ValueError(f"Body cannot be a coroutine, forgot await?")
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
            error_text = f"Error in processing handler output: {str(err)}"
            logger.error(error_text)
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
                    if not isinstance(chunk, bytes):
                        raise TypeError(
                            f"Body chunk must be str or bytes, not {type(chunk)}"
                        )
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
                error_text = f"{type(err).__name__} in chunked response: {str(err)}"
                logger.error(error_text, exc_info=err)
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
