"""
asgish - An ASGI web framework with an ASGI-ish API

Asgish is a tool to write asynchronous web applications, using as few
abstractions as possible, while still offering a friendly API. It does not
do fancy routing; it's async handlers all the way down.
"""

from ._request import BaseRequest, HttpRequest, WebsocketRequest
from ._app import handler2asgi
from ._run import run


__all__ = ["BaseRequest", "HttpRequest", "WebsocketRequest", "handler2asgi", "run"]

__version__ = "0.2.0"
