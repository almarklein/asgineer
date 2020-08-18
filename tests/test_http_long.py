"""
Test behavior for HTTP request like streams, long-polling, and SSE.
"""

import gc
import time
import asyncio

import asgineer

from common import make_server, get_backend
from pytest import raises, skip


def test_stream1():
    # Stream version using an async gen (old-style)
    async def stream_handler(request):
        async def stream():
            for i in range(10):
                await asgineer.sleep(0.1)
                yield str(i)

        return 200, {}, stream()

    with make_server(stream_handler) as p:
        res = p.get("/")

    assert res.body == b"0123456789"
    assert not p.out


def test_stream2():
    # New-style stream version
    async def stream_handler(request):
        await request.accept(200, {})
        for i in range(10):
            await asgineer.sleep(0.1)
            await request.send(str(i))

    with make_server(stream_handler) as p:
        res = p.get("/")

    assert res.body == b"0123456789"
    assert not p.out


def test_stream3():
    # This is basically long polling
    async def stream_handler(request):
        await request.accept(200, {})
        await request.sleep_while_connected(1.0)
        for i in range(10):
            await request.send(str(i))

    with make_server(stream_handler) as p:
        res = p.get("/")

    assert res.body == b"0123456789"
    assert not p.out

    if get_backend() == "mock":

        # The mock server will close the connection directly when we do not
        # use GET. So we can test that kind of behavior.
        with make_server(stream_handler) as p:
            res = p.put("/")
        assert res.body == b""
        assert not p.out

        # With POST it will even behave a bit shitty, but in a way we could
        # expect a server to behave (receive() returning None).
        with make_server(stream_handler) as p:
            res = p.post("/")
        assert res.body == b""
        assert not p.out


def test_stream4():
    # This is basically sse
    async def stream_handler(request):
        await request.accept(200, {})
        for i in range(10):
            await request.sleep_while_connected(0.1)
            await request.send(str(i))

    with make_server(stream_handler) as p:
        res = p.get("/")

    assert res.body == b"0123456789"
    assert not p.out


def test_stream5():
    # This is real sse (from the server side)
    async def stream_handler(request):
        sse_headers = {
            "content-type": "text/event-stream",
            "cache-control": "no-cache",
            "connection": "keep-alive",
        }
        await request.accept(200, sse_headers)
        for i in range(10):
            await request.sleep_while_connected(0.1)
            await request.send(f"event: message\ndata:{str(i)}\n\n")

    with make_server(stream_handler) as p:
        res = p.get("/")

    val = "".join(x.split("data:")[-1] for x in res.body.decode().split("\n\n"))
    assert val == "0123456789"


def test_stream_wakeup():

    # This tests that the request object has a wakeup (async) method.
    # And that the signal is reset when sleep_while_connected() is entered.

    async def stream_handler(request):
        await request.accept(200, {})
        await request.wakeup()  # internal knowledge: signal does not yet exist
        await request.sleep_while_connected(0.01)  # force signal to be created
        await request.wakeup()  # signal exists
        await request.sleep_while_connected(1.0)
        for i in range(10):
            await request.send(str(i))

    t0 = time.perf_counter()
    with make_server(stream_handler) as p:
        res = p.get("/")
    t1 = time.perf_counter()

    assert res.body == b"0123456789"
    assert not p.out
    assert 1 < (t1 - t0) < 3  # probably like 1.1


def test_evil_handler():
    # If, due to a "typo", the DisconnectedError is swallowed, trying
    # to use the connection will raise IOError (which means invalid use)

    if get_backend() != "mock":
        skip("Can only test this with mock server")

    async def stream_handler(request):
        await request.accept(200, {})
        while True:
            try:
                await request.sleep_while_connected(0.1)
            except asgineer.DisconnectedError:
                pass
            await request.send(b"x")

    with make_server(stream_handler) as p:
        res = p.put("/")

    assert res.body == b"x"
    assert "already disconnected" in p.out.lower()


def test_request_set():

    loop = asyncio.get_event_loop()

    s1 = asgineer.RequestSet()
    r1 = asgineer.BaseRequest(None)
    r2 = asgineer.BaseRequest(None)
    r3 = asgineer.BaseRequest(None)

    s1.add(r1)
    s1.add(r2)

    with raises(TypeError):
        s1.add("not a request object")

    # Put it in more sets
    s2 = asgineer.RequestSet()
    s3 = asgineer.RequestSet()
    for r in s1:
        s2.add(r)
        s3.add(r)

    # We only add r3 to s1, otherwise the gc test becomes flaky for some reason
    s1.add(r3)

    assert len(s1) == 3
    assert len(s2) == 2
    assert len(s3) == 2

    # Empty s3
    s3.discard(r1)
    assert len(s3) == 1
    s3.clear()
    assert len(s3) == 0

    # Asgineer app does this at the end
    loop.run_until_complete(r1._destroy())
    loop.run_until_complete(r2._destroy())
    assert len(s1) == 1
    assert len(s2) == 0

    # But the set items are weak refs too
    del r3
    gc.collect()

    assert len(s1) == 0
    assert len(s2) == 0
    assert len(s3) == 0


if __name__ == "__main__":
    test_stream_wakeup()
    test_evil_handler()

    test_request_set()

    test_stream1()
    test_stream2()
    test_stream3()
    test_stream4()
    test_stream5()
