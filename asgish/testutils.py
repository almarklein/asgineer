"""
Utilities for writing tests with Asgish handlers.
"""

import os
import sys
import time
import inspect
import asyncio
import tempfile
import subprocess
from collections import namedtuple
from wsgiref.handlers import format_date_time
from urllib.parse import unquote, urlparse

import requests

import asgish


Response = namedtuple("Respone", ["status", "headers", "body"])

testfilename = os.path.join(
    tempfile.gettempdir(), f"asgish_test_script_{os.getpid()}.py"
)

PORT = 49152 + os.getpid() % 16383  # hash pid to ephimeral port number
URL = f"http://127.0.0.1:{PORT}"

# todo: allow running multiple processes at the same time, by including a sequence number


class BaseTestServer:
    """ Base class for test servers. Objects of this class represent an ASGI
    server instance that can be used to test your server implementation.
    
    The server can be started/stopped by using it as a context manager.
    The ``url`` attribute represents the url that can be used to make
    requests to the server. When the server has stopped, The ``out``
    attribute contains the server output (stdout and stderr).
    
    Only one instance of this class (per process) should be used (as a
    context manager) at any given time.
    """

    def __init__(self, app, server_description):
        self._app = app
        self._server = server_description
        self._out = ""
        # Get stdout funcs because the mock server hijacks them
        self._stdout_write = sys.stdout.write
        self._stdout_flush = sys.stdout.flush

    @property
    def app(self):
        """ The application object that was given at instantiation.
        """
        return self._app

    @property
    def url(self):
        """ The url at which the server is listening.
        """
        return URL

    @property
    def out(self):
        """ The stdout / stderr of the server. This gets set when the
        with-statement using this object exits.
        """
        return self._out

    def __enter__(self):
        self.log(f"  Spawn {self._server} server .. ", end="")
        self._out = ""
        t0 = time.time()

        self._start_server()

        self.log(f" {time.time()-t0:0.1f}s ", end="")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.log("- Closing .. " if exc_value is None else "Error .. ", end="")
        t0 = time.time()

        out = self._stop_server()
        self._out = "\n".join(self.filter_lines(out.splitlines()))

        if exc_value is None:
            self.log(f" {time.time()-t0:0.1f}s ")
        else:
            self.log("Process output:")
            self.log(self.out)

    def get(self, url, data=None, headers=None, **kwargs):
        """ Send a GET request to the server. See request() for detais.
        """
        return self.request("GET", url, data=data, headers=headers, **kwargs)

    def put(self, url, data=None, headers=None, **kwargs):
        """ Send a PUT request to the server. See request() for detais.
        """
        return self.request("PUT", url, data=data, headers=headers, **kwargs)

    def post(self, url, data=None, headers=None, **kwargs):
        """ Send a POST request to the server. See request() for detais.
        """
        return self.request("POST", url, data=data, headers=headers, **kwargs)

    def delete(self, url, data=None, headers=None, **kwargs):
        """ Send a DELETE request to the server. See request() for detais.
        """
        return self.request("DELETE", url, data=data, headers=headers, **kwargs)

    def request(self, method, url, data=None, headers=None, **kwargs):
        """ Send a request to the server. Use the ``url`` property to get the base
        url. Returns a named tuple ``(status, headers, body)``.
        
        Arguments:
            method (str): the HTTP method (e.g. "GET")
            url (str): the url (also see the ``url`` property).
            data: the bytes to send (optional).
            headers: headers to send (optional).
            kwargs: additional arguments to pass to ``requests.request()``.
        
        """
        assert isinstance(method, str)
        assert isinstance(url, str)

        status, headers, body = self._request(
            method, url, data=data, headers=headers, **kwargs
        )
        return Response(status, headers, body)

    def log(self, *messages, sep=" ", end="\n"):
        """ Log a message. Overloadable. Default write to stdout.
        """
        msg = sep.join(str(m) for m in messages)
        self._stdout_write(msg + end)
        self._stdout_flush()

    def filter_lines(self, lines):
        """ Overloadable line filter.
        """
        return lines


START_CODE = """
import os
import sys
import time
import threading
import _thread

import asgish

def closer():
    while os.path.isfile(__file__):
        time.sleep(0.01)
    _thread.interrupt_main()

app = APP

async def stub_responder(receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})

def proxy_app(scope):
    if scope["path"].startswith("/specialtestpath/"):
        return stub_responder
    else:
        return app(scope)

if __name__ == "__main__":
    threading.Thread(target=closer).start()
    asgish.run("__main__:proxy_app", "ASGISERVER", "localhost:PORT")
    sys.stdout.flush()
    sys.exit(0)
"""

LOAD_MODULE_CODE = """
import importlib
def load_module(name, filename):
    assert filename.endswith('.py')
    if name in sys.modules:
        return sys.modules[name]
    if '.' in name:
        load_module(name.rsplit('.', 1)[0], os.path.join(os.path.dirname(filename), '__init__.py'))
    spec = importlib.util.spec_from_file_location(name, filename)
    return spec.loader.load_module()
"""


class ProcessTestServer(BaseTestServer):
    """ Test server that runs an actual server in a subprocess. The ``server``
    argument must be a server supported by Asgish' ``run()`` function, like
    "uvicorn", "hypercorn" or "daphne".
    
    This provides a very realistic approach to test server applicationes, though
    the overhead of starting and stopping the server costs about a second,
    and its hard to measure code coverage in this way. Therefore this approach
    is most suited for higher level / integration tests.
    
    Requests can be done via the methods of this object, or using any other
    request library.
    """

    def __init__(self, app, server):
        super().__init__(app, server)
        self._app_code = self._get_app_code(app)

    def _get_app_code(self, app):
        mod = inspect.getmodule(app)
        modname = "_main_" if mod.__name__ == "__main__" else mod.__name__
        is_handler = inspect.iscoroutinefunction(app)
        name1 = app.__name__
        name2 = "handler" if is_handler else "app"

        if getattr(mod, name1, None) is app:
            # We can import the app - safest option since app may have deps
            code = LOAD_MODULE_CODE
            code += f"sys.path.insert(0, '')\n" + code
            if "." not in mod.__name__:
                code += f"sys.path.insert(0, {os.path.dirname(mod.__file__)!r})\n"
            code += f"{name2} = load_module({modname!r}, {mod.__file__!r}).{name1}"

        else:
            # Likely a app defined inside a function. Get app from sourece code.
            # This will not work if the app has dependencies.
            sourcelines = inspect.getsourcelines(app)[0]
            indent = inspect.indentsize(sourcelines[0])
            code = "\n".join(line[indent:] for line in sourcelines)
            code = code.replace("def " + app.__name__, "def {name2}")

        if is_handler:
            code += f"\napp = asgish.to_asgi({name2})"
        return code

    def _start_server(self):
        # Prepare code
        code = START_CODE.replace("ASGISERVER", self._server).replace("PORT", str(PORT))
        code = code.replace("app = APP", self._app_code)
        with open(testfilename, "wb") as f:
            f.write((code).encode())
        # Start server, clean up the temp filename on failure since __exit__ wont be called.
        try:
            self._start_subprocess()
        except Exception as err:
            self._delfile()
            raise err

    def _start_subprocess(self):
        # Start subprocess. Don't use stdin; it breaks multiprocessing somehow!
        self._p = subprocess.Popen(
            [sys.executable, testfilename],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        # Wait for process to start, and make sure it is not dead
        while self._p.poll() is None:
            time.sleep(0.02)
            try:
                requests.get(URL + "/specialtestpath/init", timeout=0.01)
                break
            except requests.ConnectionError:
                pass
        if self._p.poll() is not None:
            raise RuntimeError(
                "Process failed to start!\n" + self._p.stdout.read().decode()
            )

    def _stop_server(self):
        # Ask process to stop
        self._delfile()
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
        # Get output
        return self._p.stdout.read().decode(errors="ignore")

    def _delfile(self):
        try:
            os.remove(testfilename)
        except Exception:
            pass

    def _request(self, method, url, **kwargs):
        r = requests.request(method, url, **kwargs)
        return r.status_code, r.headers, r.content


class MockTestServer(BaseTestServer):
    """ Test server that mocks an ASGI server and operates in-process.
    This is a less realistic approach, but faster and allows tracking
    test coverage, so it's more suited for unit tests.
    
    Requests *must* be done via the methods of this object. The used url
    can be anything.
    """

    def __init__(self, app, loop=None):
        super().__init__(app, "mock")

        if inspect.iscoroutinefunction(app):
            self._asgi_app = asgish.to_asgi(app)
        else:
            self._asgi_app = app

        self._loop = asyncio.get_event_loop() if loop is None else loop
        self._out_writes = []

    def _write(self, msg):
        self._out_writes.append(msg)

    def _start_server(self):
        self._out_writes = []
        self._ori_streams = sys.stdout.write, sys.stderr.write
        sys.stdout.write = sys.stderr.write = self._write

        try:
            self._lifespan_messages = []
            self._lifespan_completes = []
            self._lifespan_task = self._make_lifespan_task()
            self._wait_for_lifespan_complete("startup")
        except Exception as err:
            self._restore_streams()
            raise err

    def _restore_streams(self):
        sys.stdout.write, sys.stderr.write = self._ori_streams

    def _stop_server(self):
        try:
            self._wait_for_lifespan_complete("cleanup")
        except Exception as err:
            self._restore_streams()
            raise err
        else:
            self._restore_streams()
        return "".join(self._out_writes)

    def _make_lifespan_task(self):
        scope = {"type": "lifespan"}
        app_object = self._asgi_app(scope)

        async def receive():
            while True:
                if self._lifespan_messages:
                    return self._lifespan_messages.pop(0)
                await asyncio.sleep(0.02)

        async def send(m):
            self._lifespan_completes.append(m["type"])

        return self._loop.create_task(app_object(receive, send))

    def _wait_for_lifespan_complete(self, what, timeout=5):
        what_complete = f"lifespan.{what}.complete"

        async def waiter():
            etime = time.time() + timeout
            while what_complete not in self._lifespan_completes:
                if self._lifespan_task.done():
                    raise RuntimeError(
                        f"Lifespan task finished without producing {what}"
                    )
                if time.time() > etime:
                    raise RuntimeError(
                        f"Timeout for {what}, has {self._lifespan_completes}"
                    )
                await asyncio.sleep(0.02)

        self._lifespan_messages.append({"type": f"lifespan.{what}"})
        self._loop.run_until_complete(waiter())

    def _request(self, method, url, **kwargs):
        co = self._co_request(method, url, **kwargs)
        return self._loop.run_until_complete(co)

    async def _co_request(self, method, url, **kwargs):
        req = requests.Request(method, url, **kwargs)
        p = req.prepare()  # Get the "resolved" request
        p.headers.setdefault("user-agent", "asgi_mock_server")

        scope = self._make_scope(p)

        app_object = self._asgi_app(scope)

        outgoing_chunks = []
        if p.body is not None:
            outgoing_chunks.append(p.body)

        async def receive():
            if outgoing_chunks:
                chunk = outgoing_chunks.pop(0)
                return {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": bool(outgoing_chunks),
                }
            else:
                return {"type": "http.disconnect"}

        incoming_chunks = []
        response = []

        async def send(m):
            if m["type"] == "http.response.start":
                headers = dict((h[0].decode(), h[1].decode()) for h in m["headers"])
                headers.setdefault("date", format_date_time(time.time()))
                headers.setdefault("server", "asgish_mock_server")
                response.extend([m["status"], headers])
            elif m["type"] == "http.response.body":
                incoming_chunks.append(m["body"])
            else:
                pass  # ignore?

        await app_object(receive, send)
        response.append(b"".join(incoming_chunks))
        return tuple(response)

    def _make_scope(self, request):
        scheme, netloc, path, params, query, fragement = urlparse(request.url)
        if ":" in netloc:
            host, port = netloc.split(":", 1)
            port = int(port)
        else:
            host = netloc
            port = {"http": 80, "ws": 80, "https": 443, "wss": 443}[scheme]

        # Include the 'host' header.
        if "host" in request.headers:
            headers = []
        elif port == 80:
            headers = [[b"host", host.encode()]]
        else:
            headers = [[b"host", ("%s:%d" % (host, port)).encode()]]

        # Include other request headers.
        headers += [
            [key.lower().encode(), value.encode()]
            for key, value in request.headers.items()
        ]

        return {
            "type": "http",
            "http_version": "1.1",
            "method": request.method,
            "path": unquote(path),
            "root_path": "",
            "scheme": scheme,
            "query_string": query.encode(),
            "headers": headers,
            "client": ["testclient", 50000],
            "server": [host, port],
        }
