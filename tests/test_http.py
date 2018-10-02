import os
import sys
import json
import time
import inspect
import subprocess

import requests
import pytest

from asgish import handler2asgi

port = 8888
url = f"http://127.0.0.1:{port}"


THIS_DIR = os.path.dirname(os.path.abspath(__file__))

testfilename = os.path.join(THIS_DIR, "asgish_test.py")

START_CODE = f"""
import os
import sys
import time
import threading
import _thread

def closer():
    while os.path.isfile(__file__):
        time.sleep(0.01)
    _thread.interrupt_main()

if __name__ == "__main__":
    
    threading.Thread(target=closer).start()
    sys.stdout.write("START\\n")
    sys.stdout.flush()
    run("__main__:app", "asgiservername", "localhost:{port}", log_level="warning")
    sys.exit(0)
"""


def getbackend():
    return os.environ.get("ASGISH_SERVER", "uvicorn").lower()


class ServerProcess:
    """ Helper class to run a handler in a subprocess, as a context manager.
    """

    def __init__(self, handler):
        self._handler_code = inspect.getsource(handler)
        self._handler_code += "\nfrom asgish import handler2asgi, run\n"
        self._handler_code += f"\napp = handler2asgi({handler.__name__})\n"
        self.out = ""

    def __enter__(self):
        print(".", end="")
        # Prepare code
        start_code = START_CODE.replace("asgiservername", getbackend())
        with open(testfilename, "wb") as f:
            f.write((self._handler_code + start_code).encode())
        # Start subprocess. Don't use stdin; it breaks multiprocessing somehow!
        self._p = subprocess.Popen(
            [sys.executable, testfilename],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        # Wait for process to start, and make sure it is not dead
        while (
            self._p.poll() is None
            and self._p.stdout.readline().decode().strip() != "START"
        ):
            time.sleep(0.01)
        time.sleep(0.2)  # Wait a bit more, to be sure the server is up
        if self._p.poll() is not None:
            raise RuntimeError(
                "Process failed to start!\n" + self._p.stdout.read().decode()
            )
        print(".", end="")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("." if exc_value is None else "e", end="")
        # Ask process to stop
        try:
            os.remove(testfilename)
        except Exception:
            pass

        # Force it to stop if needed
        for i in range(10):
            etime = time.time() + 0.5
            while self._p.poll() is None and time.time() < etime:
                time.sleep(0.01)
            if self._p.poll() is not None:
                break
            self._p.terminate()
        else:
            raise RuntimeError("Runaway server process failed to terminate!")

        # Get output, remove stuff that we dont need
        lines = self._p.stdout.read().decode(errors="ignore").splitlines()
        self.out = "\n".join(
            line for line in lines if not line.startswith("Running on http")
        )

        if exc_value is None:
            print(".")
        else:
            print("  Process output:")
            print(self.out)


def test_backend_reporter(capsys=None):
    """ A stub test to display the used backend.
    """
    msg = f"  Running tests with ASGI server: {getbackend()}"
    if capsys:
        with capsys.disabled():
            print(msg)
    else:
        print(msg)


## Test normal usage


async def handler1(request):
    return 200, {"xx-foo": "x"}, "hi!"


async def handler2(request):
    async def handler1(request):
        return 200, {"xx-foo": "x"}, "hi!"

    return await handler1(request)


async def handler3(request):
    async def handler1(request):
        return 200, {"xx-foo": "x"}, "hi!"

    async def handler2(request):
        return await handler1(request)

    return await handler2(request)


async def handler4(request):
    return "ho!"


async def handler5(request):
    return ("ho!",)


async def handler6(request):
    return 400, "ho!"


async def handler7(request):
    return {"xx-foo": "x"}, "ho!"


async def handler_json1(request):
    return {"foo": 42, "bar": 7}


async def handler_html1(request):
    return "<!DOCTYPE html> <html>foo</html>"


async def handler_html2(request):
    return "<html>foo</html>"


def test_normal_usage():

    # Test normal usage

    with ServerProcess(handler1) as p:
        res = requests.get(url)

    # res.status_code, res.reason, res.headers, , res.content
    print(res.content)
    print(res.headers)
    print(p.out)

    assert res.status_code == 200
    assert res.content.decode() == "hi!"
    assert not p.out

    # Daphne capitalizes the header keys, hypercorn aims at lowercase
    refheaders = {"content-type", "content-length", "xx-foo"}
    if getbackend() not in "daphne":
        refheaders.update({"server", "date"})
    assert set(k.lower() for k in res.headers.keys()) == refheaders
    assert res.headers["content-type"] == "text/plain"
    assert res.headers["content-length"] == "3"  # yes, a string

    # Test delegation to other handler

    with ServerProcess(handler2) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.content.decode() == "hi!"
    assert not p.out
    assert "xx-foo" in res.headers

    # Test delegation to yet other handler

    with ServerProcess(handler3) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.content.decode() == "hi!"
    assert not p.out
    assert "xx-foo" in res.headers


def test_output_shapes():

    # Singleton arg

    with ServerProcess(handler4) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.content.decode() == "ho!"
    assert not p.out

    with ServerProcess(handler5) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.content.decode() == "ho!"
    assert not p.out

    # Two element tuple (two forms)

    with ServerProcess(handler6) as p:
        res = requests.get(url)

    assert res.status_code == 400
    assert res.content.decode() == "ho!"
    assert not p.out

    with ServerProcess(handler7) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.content.decode() == "ho!"
    assert not p.out
    assert "xx-foo" in res.headers


def test_body_types():

    # Plain text

    with ServerProcess(handler4) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.headers["content-type"] == "text/plain"
    assert res.content.decode()
    assert not p.out

    # Json

    with ServerProcess(handler_json1) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/json"
    assert res.json() == {"foo": 42, "bar": 7}
    assert not p.out

    # HTML

    with ServerProcess(handler_html1) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.headers["content-type"] == "text/html"
    assert "foo" in res.content.decode()
    assert not p.out

    with ServerProcess(handler_html2) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.headers["content-type"] == "text/html"
    assert "foo" in res.content.decode()
    assert not p.out


## Test request object


async def handle_request_object2(request):
    assert request.scope["method"] == request.method
    d = dict(
        url=request.url,
        headers=request.headers,
        querylist=request.querylist,
        querydict=request.querydict,
        bodystring=(await request.get_body()).decode(),
        json=await request.get_json(),
    )
    return 200, d


def test_request_object():

    with ServerProcess(handle_request_object2) as p:
        res = requests.post(url + "/xx/yy?arg=3&arg=4", b'{"foo": 42}')

    assert res.status_code == 200
    assert not p.out

    d = res.json()
    assert d["url"] == "http://127.0.0.1:8888/xx/yy?arg=3&arg=4"
    assert "user-agent" in d["headers"]
    assert d["querylist"] == [["arg", "3"], ["arg", "4"]]  # json makes tuples lists
    assert d["querydict"] == {"arg": "4"}
    assert json.loads(d["bodystring"]) == {"foo": 42}
    assert d["json"] == {"foo": 42}


## Chunking


async def handler_chunkwrite1(request):
    async def asynciter():
        yield "foo"
        yield "bar"

    return 200, {}, asynciter()


async def handler_chunkread1(request):
    body = []
    async for chunk in request.iter_body():
        body.append(chunk)
    return b"".join(body)


async def handler_chunkread2(request):
    return request.iter_body()  # echo :)


def test_chunking():

    # Write

    with ServerProcess(handler_chunkwrite1) as p:
        res = requests.get(url)

    assert res.status_code == 200
    assert res.content.decode() == "foobar"
    assert not p.out

    # Read

    with ServerProcess(handler_chunkread1) as p:
        res = requests.post(url, b"foobar")

    assert res.status_code == 200
    assert res.content.decode() == "foobar"
    assert not p.out

    # Both

    with ServerProcess(handler_chunkread2) as p:
        res = requests.post(url, b"foobar")

    assert res.status_code == 200
    assert res.content.decode() == "foobar"
    assert not p.out


## Test exceptions and errors


async def handler_err1(request):
    return 501, {"xx-custom": "xx"}, "oops"


async def handler_err2(request):
    raise ValueError("woops")
    return 200, {"xx-custom": "xx"}, "oops"


async def handler_err3(request):
    async def chunkiter():
        raise ValueError("woops")
        yield "foo"

    return 200, {"xx-custom": "xx"}, chunkiter()


async def handler_err4(request):
    async def chunkiter():
        yield "foo"
        raise ValueError("woops")  # too late to do a status 500

    return 200, {"xx-custom": "xx"}, chunkiter()


def test_errors():

    # Explicit error

    with ServerProcess(handler_err1) as p:
        res = requests.get(url)

    assert not res.ok
    assert res.status_code == 501
    assert res.content.decode() == "oops"
    assert not p.out
    assert "xx-custom" in res.headers

    # Exception in handler

    with ServerProcess(handler_err2) as p:
        res = requests.get(url)

    assert not res.ok
    assert res.status_code == 500
    assert "error in request handler" in res.content.decode().lower()
    assert "woops" in res.content.decode()
    assert "woops" in p.out
    assert p.out.count("woops") == 1
    assert "xx-custom" not in res.headers

    # Exception in handler with chunked body

    with ServerProcess(handler_err3) as p:
        res = requests.get(url)

    assert not res.ok
    assert res.status_code == 500
    assert "error in chunked response" in res.content.decode().lower()
    assert "woops" in res.content.decode()
    assert "woops" in p.out and "foo" not in p.out
    assert "xx-custom" not in res.headers

    # Exception in handler with chunked body, too late

    with ServerProcess(handler_err4) as p:
        res = requests.get(url)

    assert res.ok  # no fail, just got half the page ...
    assert res.status_code == 200
    assert res.content.decode() == "foo"
    assert "woops" in p.out
    assert "xx-custom" in res.headers


## Test wrong output


async def handler_output1(request):
    return 200, {}, "foo", "bar"


async def handler_output2(request):
    return 0


async def handler_output3(request):
    return [200, {}, "foo"]


async def handler_output4(request):
    return "200", {}, "foo"


async def handler_output5(request):
    return 200, 4, "foo"


async def handler_output6(request):
    return 200, {}, 4


async def handler_output11(request):
    async def chunkiter():
        yield 3
        yield "foo"

    return 200, {"xx-custom": "xx"}, chunkiter()


async def handler_output12(request):
    async def chunkiter():
        yield "foo"
        yield 3  # too late to do a status 500

    return 200, {"xx-custom": "xx"}, chunkiter()


def test_wrong_output():

    with ServerProcess(handler_output1) as p:
        res = requests.get(url)

    assert res.status_code == 500
    assert "handler returned 4-tuple" in res.content.decode().lower()
    assert "handler returned 4-tuple" in p.out.lower()

    for handler in (handler_output2, handler_output3, handler_output6):
        with ServerProcess(handler_output2) as p:
            res = requests.get(url)

        assert res.status_code == 500
        assert "body cannot be" in res.content.decode().lower()
        assert "body cannot be" in p.out.lower()

    with ServerProcess(handler_output4) as p:
        res = requests.get(url)

    assert res.status_code == 500
    assert "status code must be an int" in res.content.decode().lower()
    assert "status code must be an int" in p.out.lower()

    with ServerProcess(handler_output5) as p:
        res = requests.get(url)

    assert res.status_code == 500
    assert "headers must be a dict" in res.content.decode().lower()
    assert "headers must be a dict" in p.out.lower()

    # Chunked

    with ServerProcess(handler_output11) as p:
        res = requests.get(url)

    assert res.status_code == 500
    assert "error in chunked response" in res.content.decode().lower()
    assert "body chunk must be" in res.content.decode().lower()
    assert "body chunk must be" in p.out.lower()

    with ServerProcess(handler_output12) as p:
        res = requests.get(url)

    assert res.status_code == 200  # too late to set status!
    assert res.content.decode() == "foo"
    assert "body chunk must be" in p.out.lower()


## Test wrong usage


def handler_wrong_use1(request):
    return 200, {}, "hi"


async def handler_wrong_use2(request):
    yield 200, {}, "hi"


def test_wrong_use():

    with pytest.raises(TypeError):
        handler2asgi(handler_wrong_use1)

    with pytest.raises(TypeError):
        handler2asgi(handler_wrong_use2)


##

if __name__ == "__main__":

    # Select backend with cli arg
    for arg in sys.argv:
        if arg.upper().startswith("--ASGISH_SERVER="):
            os.environ["ASGISH_SERVER"] = arg.split("=")[1].strip().lower()

    # Run all test functions
    for func in list(globals().values()):
        if callable(func) and func.__name__.startswith("test_"):
            print(f"Running {func.__name__} ...")
            func()
    print("Done")

    # with ServerProcess(handler_err2) as p:
    #     time.sleep(10)
