"""
Utilities for writing tests with Asgish handlers.
"""

import os
import sys
import time
import inspect
import tempfile
import subprocess
from urllib.request import urlopen


testfilename = os.path.join(
    tempfile.gettempdir(), f"asgish_test_script_{os.getpid()}.py"
)

PORT = 49152 + os.getpid() % 16383  # hash pid to ephimeral port number

# os.environ.setdefault("COVERAGE_PROCESS_START", ".coveragerc")

START_CODE = f"""
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

handler = X

async def proxy_handler(request):
    if request.path.startswith("/specialtestpath/"):
        return "OK"
    return await handler(request)

app = asgish.to_asgi(proxy_handler)

if __name__ == "__main__":
    threading.Thread(target=closer).start()
    asgish.run("__main__:app", "asgiservername", "localhost:{PORT}")
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


class ServerProcess:
    """ Create a server that runs in a subprocess. Use as a context manager to
    start and stop the server. The ``url`` attribute represents the url
    that can be used to make requests to the server. When the server has stopped,
    The ``out`` attribute contains the server output (stdout and stderr).
    
    Only one instance of this class (per process) should be used (as a
    context manager) at any given time.
    """

    def __init__(self, backend, handler):
        self._backend = backend
        self._handler_code = self._get_handler_code(handler)
        self.url = f"http://127.0.0.1:{PORT}"

    def _get_handler_code(self, handler):
        mod = inspect.getmodule(handler)
        modname = "_main_" if mod.__name__ == "__main__" else mod.__name__
        hname = handler.__name__

        if getattr(mod, hname, None) is handler:
            # We can import the handler - safest option since handler may have deps
            code = LOAD_MODULE_CODE
            code += f"sys.path.insert(0, '')\n" + code
            if "." not in mod.__name__:
                code += f"sys.path.insert(0, {os.path.dirname(mod.__file__)!r})\n"
            code += f"handler = load_module({modname!r}, {mod.__file__!r}).{hname}"

        else:
            # Likely a handler defined inside a function. Get handler from sourece code.
            # This will not work if the handler has dependencies.
            sourcelines = inspect.getsourcelines(handler)[0]
            indent = inspect.indentsize(sourcelines[0])
            code = "\n".join(line[indent:] for line in sourcelines)
            code = code.replace("def " + handler.__name__, "def handler")

        return code

    def __enter__(self):
        self.out = ""
        self._print("Spawning server ... ", end="")

        # Prepare code
        start_code = START_CODE.replace("asgiservername", self._backend)
        start_code = start_code.replace("handler = X", self._handler_code)
        with open(testfilename, "wb") as f:
            f.write((start_code).encode())

        # Start server, clean up the temp filename on failure since __exit__ wont be called.
        t0 = time.time()
        try:
            self._start_server()
        except Exception as err:
            self._delfile()
            raise err
        self._print(f"in {time.time()-t0:0.2f}s. ", end="")

        return self

    def _start_server(self):
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
                urlopen(self.url + "/specialtestpath/init")
                break
            except Exception:
                pass
        if self._p.poll() is not None:
            raise RuntimeError(
                "Process failed to start!\n" + self._p.stdout.read().decode()
            )

    def __exit__(self, exc_type, exc_value, traceback):
        self._print("- Closing ... " if exc_value is None else "Error ... ", end="")
        t0 = time.time()
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

        # Get output and filter
        lines = self._p.stdout.read().decode(errors="ignore").splitlines()
        self.out = "\n".join(self._filter_lines(lines))

        if exc_value is None:
            self._print(f"in {time.time()-t0:0.2f}s. ")
        else:
            self._print("Process output:")
            self._print(self.out)

    def _delfile(self):
        try:
            os.remove(testfilename)
        except Exception:
            pass

    def _print(self, msg, end="\n"):
        print(msg, end=end)

    def _filter_lines(self, lines):
        """ Overloadable line filter.
        """
        return lines
