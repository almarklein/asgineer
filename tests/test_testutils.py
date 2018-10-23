"""
Test testutils code. Note that most other tests implicitly test it.
"""

from common import make_server


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


if __name__ == "__main__":
    from common import run_tests, set_backend_from_argv

    set_backend_from_argv()
    run_tests(globals())
