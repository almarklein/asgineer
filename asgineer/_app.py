"""
This module implements an ASGI application class that forms the adapter
between the user-defined handler function and the ASGI server.
"""

import sys
import json
import logging
import inspect
from . import _request
from ._request import HttpRequest, WebsocketRequest, DisconnectedError

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


def to_asgi(handler):
    """ Convert a request handler (a coroutine function) to an ASGI
    application, which can be served with an ASGI server, such as
    Uvicorn, Hypercorn, Daphne, etc.
    """

    if not inspect.iscoroutinefunction(handler):
        raise TypeError(
            "asgineer.to_asgi() handler function must be a coroutine function."
        )

    async def application_wrapper(scope, receive, send):
        return await asgineer_application(handler, scope, receive, send)

    application_wrapper.__module__ = handler.__module__
    application_wrapper.__name__ = handler.__name__
    application_wrapper.__doc__ = handler.__doc__
    application_wrapper.asgineer_handler = handler
    return application_wrapper


async def asgineer_application(handler, scope, receive, send):

    # server_version = scope["asgi"].get("version", "2.0")
    # spec_version = scope["asgi"].get("spec_version", "2.0")

    if scope["type"] == "http":
        request = HttpRequest(scope, receive, send)
        await _handle_http(handler, request)
    elif scope["type"] == "websocket":
        request = WebsocketRequest(scope, receive, send)
        await _handle_websocket(handler, request)
    elif scope["type"] == "lifespan":
        await _handle_lifespan(receive, send)
    else:
        logger.warning(f"Unknown ASGI type {scope['type']}")


async def _handle_lifespan(receive, send):
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            try:
                # Could do startup stuff here
                logger.info("Server is starting up")
            except Exception as err:  # pragma: no cover
                await send({"type": "lifespan.startup.failed", "message": str(err)})
            else:
                await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            try:
                # Could do shutdown stuff here
                logger.info("Server is shutting down")
            except Exception as err:  # pragma: no cover
                await send({"type": "lifespan.shutdown.failed", "message": str(err)})
            else:
                await send({"type": "lifespan.shutdown.complete"})
            return
        else:
            logger.warning(f"Unknown lifespan message {message['type']}")


async def _handle_http(handler, request):

    try:

        # Call request handler to get the result
        where = "request handler"
        result = await handler(request)

        if request._app_state == _request.CONNECTING:
            # Process the handler output
            where = "processing handler output"
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
                # Returning an async generator used to be THE way to do chunked
                # responses before version 0.8. We keep it for backwards
                # compatibility, and because it can be quite nice.
                pass
            else:
                if inspect.isgenerator(body):
                    raise ValueError(
                        "Body cannot be a regular generator, use an async generator."
                    )
                elif inspect.iscoroutine(body):
                    raise ValueError("Body cannot be a coroutine, forgot await?")
                else:
                    raise ValueError(f"Body cannot be {type(body)}.")
            # Send response. Note that per the spec, if we do not specify
            # the content-length, the server sets Transfer-Encoding to chunked.
            if isinstance(body, bytes):
                where = "sending response"
                headers.setdefault("content-length", str(len(body)))
                await request.accept(status, headers)
                await request.send(body, more=False)
            else:
                where = "sending chunked response"
                accepted = False
                async for chunk in body:
                    if not isinstance(chunk, (bytes, str)):
                        raise ValueError("Response chunks must be bytes or str.")
                    if not accepted:
                        await request.accept(status, headers)
                        accepted = True
                    await request.send(chunk)

        else:
            # If the handler accepted the request, it should use send, not return.
            if result is not None:
                raise IOError("Handlers that call request.accept() should return None.")

        # Mark end of data, if needed
        if request._app_state == _request.CONNECTED:
            where = "finalizing response"
            await request.send(b"", more=False)

    except DisconnectedError:
        pass  # Not really an error

    except Exception as err:
        # Process errors. We log them, and if possible send a 500
        error_text = f"{type(err).__name__} in {where}: {str(err)}"
        logger.error(error_text, exc_info=err)
        if request._app_state == _request.CONNECTING:
            await request.accept(500, {})
            await request.send(error_text, more=False)
        elif request._app_state == _request.CONNECTED:
            await request.send(b"", more=False)  # At least close it

    finally:

        # Clean up
        try:
            await request._destroy()
        except Exception as err:  # pragma: no cover
            logger.error(f"Error in cleanup: {str(err)}", exc_info=err)


async def _handle_websocket(handler, request):

    try:

        result = await handler(request)

        if result is not None:
            error_text = (
                "A websocket handler should return None; "
                + "use request.send() and request.receive() to communicate."
            )
            raise IOError(error_text)

    except DisconnectedError:
        pass  # Not really an error

    except Exception as err:
        error_text = f"{type(err).__name__} in websocket handler: {str(err)}"
        logger.error(error_text, exc_info=err)

    finally:

        # The ASGI spec specifies that ASGI servers should close the
        # ws connection when the task ends. At the time of writing
        # (04-10-2018), only Uvicorn does this. And at 18-08-2020 Daphne
        # still doesn't. So ... just close for good measure.
        try:
            await request.close()
        except Exception:  # pragma: no cover
            pass

        # Also clean up
        try:
            await request._destroy()
        except Exception as err:  # pragma: no cover
            logger.error(f"Error in ws cleanup: {str(err)}", exc_info=err)
