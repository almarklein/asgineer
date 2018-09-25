

import sys
import json
import random
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
    
    Application.__module__ = handler.__module__
    Application.__name__ = handler.__name__
    return Application


from asgish_ws import WebSocket


class BaseApplication:
    """ Base ASGI application class.
    """

    _handler = None

    def __init__(self, scope):
        self._scope = scope

    async def __call__(self, receive, send):
        
        if self._scope['type'] == 'http':
            request = Request(self._scope, receive)
        elif self._scope['type'] == 'websocket':
            request = WebSocket(self._scope, receive, send)
            await self._handler(request)
            return
        else:
            raise RuntimeError(f"Dont know about ASGI type {self._scope['type']}")
    
        # === Call handler to get the result
        try:

            result = await self._handler(request)

        except Exception as err:
            # Error in the handler
            errer_text = "Error in request handler: " + str(err)
            try:
                await send({"type": "http.response.start", "status": 500, "headers": []})
                await send({"type": "http.response.body", "body": errer_text.encode()})
            except Exception:
                pass
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
