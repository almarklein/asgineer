import os
import sys
import time
import inspect
import subprocess


PORT = 8888
URL = f"http://127.0.0.1:{PORT}"


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
    run("__main__:app", "asgiservername", "localhost:{PORT}", log_level="warning")
    sys.stdout.flush()
    sys.exit(0)
"""


def get_backend():
    return os.environ.get("ASGISH_SERVER", "uvicorn").lower()


def set_backend_from_argv():
    for arg in sys.argv:
        if arg.upper().startswith("--ASGISH_SERVER="):
            os.environ["ASGISH_SERVER"] = arg.split("=")[1].strip().lower()


def run_tests(scope):
    for func in list(scope.values()):
        if callable(func) and func.__name__.startswith("test_"):
            print(f"Running {func.__name__} ...")
            func()
    print("Done")


def _dedent(code):
    lines = code.splitlines()
    mindent = 100
    for line in lines:
        line = line.rstrip()
        line_ = line.lstrip()
        if line_:
            mindent = min(mindent, len(line) - len(line_))
    for i in range(len(lines)):
        lines[i] = lines[i][mindent:]
    return "\n".join(lines)


class ServerProcess:
    """ Helper class to run a handler in a subprocess, as a context manager.
    """

    def __init__(self, handler):
        self._handler_code = _dedent(inspect.getsource(handler))
        self._handler_code += "\nfrom asgish import handler2asgi, run\n"
        self._handler_code += f"\napp = handler2asgi({handler.__name__})\n"
        self.out = ""

    def __enter__(self):
        print(".", end="")
        # Prepare code
        start_code = START_CODE.replace("asgiservername", get_backend())
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
        skip = ("Running on http", "Task was destroyed but", "task: <Task pending coro")
        self.out = "\n".join(line for line in lines if not line.startswith(skip))

        if exc_value is None:
            print(".")
        else:
            print("  Process output:")
            print(self.out)
