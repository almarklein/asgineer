"""
Test some specifics of the App class.
"""

import logging
import asyncio

import asgish


class LogCapturer(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.msg)

    def __enter__(self):
        logger = logging.getLogger("asgish")
        logger.addHandler(self)
        return self

    def __exit__(self, *args, **kwargs):
        logger = logging.getLogger("asgish")
        logger.removeHandler(self)


async def handler(request):
    return ""


def test_invalid_scope_types():

    # All scope valid scope types are tested in other tests. Only test invalid here.

    app = asgish.to_asgi(handler)

    scope = {"type": "notaknownscope"}
    loop = asyncio.get_event_loop()
    with LogCapturer() as cap:
        app_ob = app(scope)
        loop.run_until_complete(app_ob(None, None))

    assert len(cap.messages) == 1
    assert "unknown" in cap.messages[0].lower() and "notaknownscope" in cap.messages[0]


def test_lifespan():

    app = asgish.to_asgi(handler)

    scope = {"type": "lifespan"}
    loop = asyncio.get_event_loop()

    lifespan_messages = [
        {"type": "lifespan.startup"},
        {"type": "lifespan.bullshit"},
        {"type": "lifespan.cleanup"},
    ]
    sent = []

    async def receive():
        return lifespan_messages.pop(0)

    async def send(m):
        sent.append(m["type"])

    with LogCapturer() as cap:
        app_ob = app(scope)
        loop.run_until_complete(app_ob(receive, send))

    assert sent == ["lifespan.startup.complete", "lifespan.cleanup.complete"]

    assert len(cap.messages) == 3
    assert cap.messages[0].lower().count("starting up")
    assert "bullshit" in cap.messages[1] and "unknown" in cap.messages[1].lower()
    assert cap.messages[2].lower().count("cleaning up")


if __name__ == "__main__":
    test_invalid_scope_types()
    test_lifespan()
