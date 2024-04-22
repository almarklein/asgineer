"""
Common utilities used in our test scripts.
"""

import os
import sys

from asgineer.testutils import ProcessTestServer, MockTestServer


def get_backend():
    return os.environ.get("ASGI_SERVER", "mock").lower()


def set_backend_from_argv():
    for arg in sys.argv:
        if arg.upper().startswith("--ASGI_SERVER="):
            os.environ["ASGI_SERVER"] = arg.split("=")[1].strip().lower()


def run_tests(scope):
    for func in list(scope.values()):
        if callable(func) and func.__name__.startswith("test_"):
            print(f"Running {func.__name__} ...")
            func()
    print("Done")


def filter_lines(lines):
    # Overloadable line filter
    skip = (
        "Running on http",  # older hypercorn
        "Running on 127.",  # older hypercorn
        "Task was destroyed but",
        "task: <Task pending coro",
        "[INFO ",
        "Aborted!",
    )
    return [line for line in lines if line and not line.startswith(skip)]


def make_server(app):
    servername = get_backend()
    if servername.lower() == "mock":
        server = MockTestServer(app)
    else:
        server = ProcessTestServer(app, servername)
    server.filter_lines = filter_lines
    return server
