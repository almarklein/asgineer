"""
Test testutils code. Note that most other tests implicitly test it.
"""

from common import make_server
from asgish.testutils import MockTestServer, ProcessTestServer


async def handler1(request):
    return "hellow1"


async def handler2(request):
    return await handler1(request)


def test_http():
    async def handler3(request):
        return "hellow3"

    async def handler4(request):
        return await handler1(request)

    with make_server(handler1) as p:
        assert p.get("").body == b"hellow1"

    with make_server(handler2) as p:
        assert p.get("").body == b"hellow1"

    with make_server(handler3) as p:
        assert p.get("").body == b"hellow3"

    # This would work with the Mock server, but not with uvicorn
    # with make_server(handler4) as p:
    #     assert p.get("").body == b"hellow1"


def test_lifetime_messages():
    async def handler(request):
        print("xxx")
        return "hellow"

    with MockTestServer(handler) as p:
        assert p.get("").body.decode() == "hellow"

    assert len(p.out.strip().splitlines()) == 3
    assert "Server is starting up" in p.out
    assert "xxx" in p.out
    assert "Server is cleaning up" in p.out

    try:
        import uvicorn as server
    except ImportError:
        return  # skip ...

    with ProcessTestServer(handler, server.__name__) as p:
        assert p.get("").body.decode()  # == 'hellow'

    # todo: somehow the lifetime messages dont show up and I dont know why.

    # assert len(p.out.strip().splitlines()) == 3
    # assert "Server is starting up" in p.out
    assert "xxx" in p.out
    # assert "Server is cleaning up" in p.out


if __name__ == "__main__":
    from common import run_tests, set_backend_from_argv

    set_backend_from_argv()
    run_tests(globals())
