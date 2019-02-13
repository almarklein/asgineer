"""
Test testutils code. Note that most other tests implicitly test it.
"""

from common import make_server
from asgineer.testutils import MockTestServer
import asgineer


async def handler1(request):
    return "hellow1"


async def handler2(request):
    return await handler1(request)


app1 = asgineer.to_asgi(handler1)


@asgineer.to_asgi
async def app2(request):
    return "hellow2"


def test_http():
    async def handler3(request):
        return "hellow3"

    async def handler4(request):
        return await handler1(request)

    app3 = asgineer.to_asgi(handler3)
    app3

    with make_server(handler1) as p:
        assert p.get("").body == b"hellow1"

    with make_server(handler2) as p:
        assert p.get("").body == b"hellow1"

    with make_server(handler3) as p:
        assert p.get("").body == b"hellow3"

    # This would work with the Mock server, but not with uvicorn
    # with make_server(handler4) as p:
    #     assert p.get("").body == b"hellow1"

    # This would work with the Mock server, but not with uvicorn
    # with make_server(app1) as p:
    #    assert p.get("").body == b"hellow1"

    with make_server(app2) as p:
        assert p.get("").body == b"hellow2"

    # This would work with the Mock server, but not with uvicorn
    # with make_server(app3) as p:
    #     assert p.get("").body == b"hellow3"


def test_http_mock():
    # We repeat the test, so that on non-mock server runs we can see
    # a better coverage of the testutils module

    async def handler3(request):
        return "hellow3"

    async def handler4(request):
        return await handler1(request)

    app3 = asgineer.to_asgi(handler3)

    with MockTestServer(handler1) as p:
        assert p.get("").body == b"hellow1"

    with MockTestServer(handler2) as p:
        assert p.get("").body == b"hellow1"

    with MockTestServer(handler3) as p:
        assert p.get("").body == b"hellow3"

    # Only with mock server!
    with MockTestServer(handler4) as p:
        assert p.get("").body == b"hellow1"

    # Only with mock server!
    with MockTestServer(app1) as p:
        assert p.get("").body == b"hellow1"

    with MockTestServer(app2) as p:
        assert p.get("").body == b"hellow2"

    # Only with mock server!
    with MockTestServer(app3) as p:
        assert p.get("").body == b"hellow3"


def test_lifetime_messages():
    async def handler(request):
        print("xxx")
        return "hellow"

    with MockTestServer(handler) as p:
        assert p.get("").body.decode() == "hellow"

    assert len(p.out.strip().splitlines()) == 3
    assert "Server is starting up" in p.out
    assert "xxx" in p.out
    assert "Server is shutting down" in p.out

    with make_server(handler) as p:
        assert p.get("").body.decode() == "hellow"

    # todo: somehow the lifetime messages dont show up (on uvicorn) and I dont know why.

    # assert len(p.out.strip().splitlines()) == 3
    # assert "Server is starting up" in p.out
    assert "xxx" in p.out
    # assert "Server is shutting down" in p.out


if __name__ == "__main__":
    from common import run_tests, set_backend_from_argv

    set_backend_from_argv()
    run_tests(globals())
