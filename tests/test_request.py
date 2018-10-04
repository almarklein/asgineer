import json

import requests

from testutils import URL, ServerProcess


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

    with ServerProcess(handle_request_object1) as p:
        res = requests.post(URL + "/xx/yy?arg=3&arg=4", b'{"foo": 42}')

    assert res.status_code == 200
    assert not p.out

    d = res.json()
    assert d["url"] == "http://127.0.0.1:8888/xx/yy?arg=3&arg=4"
    assert "user-agent" in d["headers"]
    assert d["querylist"] == [["arg", "3"], ["arg", "4"]]  # json makes tuples lists
    assert d["querydict"] == {"arg": "4"}
    assert json.loads(d["bodystring"]) == {"foo": 42}
    assert d["json"] == {"foo": 42}


if __name__ == "__main__":
    from testutils import run_tests, set_backend_from_argv

    set_backend_from_argv()
    run_tests(globals())
