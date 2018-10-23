"""
Test some specifics of the Request classes.
"""

import json

from common import make_server


async def handle_request_object1(request):
    assert request.scope["method"] == request.method
    d = dict(
        url=request.url,
        headers=request.headers,
        querylist=request.querylist,
        querydict=request.querydict,
        bodystring=(await request.get_body()).decode(),
        json=await request.get_json(),
    )
    return d


def test_request_object():

    with make_server(handle_request_object1) as p:
        res = p.post("/xx/yy?arg=3&arg=4", b'{"foo": 42}')

    assert res.status == 200
    assert not p.out

    d = json.loads(res.body.decode())
    assert d["url"] == p.url + "/xx/yy?arg=3&arg=4"
    assert "user-agent" in d["headers"]
    assert d["querylist"] == [["arg", "3"], ["arg", "4"]]  # json makes tuples lists
    assert d["querydict"] == {"arg": "4"}
    assert json.loads(d["bodystring"]) == {"foo": 42}
    assert d["json"] == {"foo": 42}


if __name__ == "__main__":
    from common import run_tests, set_backend_from_argv

    set_backend_from_argv()
    run_tests(globals())
