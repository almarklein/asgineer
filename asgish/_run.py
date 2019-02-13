"""
This module implements a ``run()`` function to start an ASGI server of choice.
"""


def run(app, server, bind="localhost:8080", **kwargs):
    """ Run the given ASGI app with the given ASGI server. (This works for
    any ASGI app, not just Asgineer apps.) This provides a generic programatic
    API as an alternative to the standard ASGI-way to start a server.
    
    Arguments:
    
    * ``app`` (required): The ASGI application object, or a string ``"module.path:appname"``.
    * ``server`` (required): The name of the server to use, e.g. uvicorn/hypercorn/etc.
    * ``kwargs``: additional arguments to pass to the underlying server.
    """

    # Compose application name
    if isinstance(app, str):
        appname = app
        if ":" not in appname:
            raise ValueError("If specifying an app by name, give its full path!")
    else:
        appname = app.__module__ + ":" + app.__name__

    # Check server and bind
    assert isinstance(server, str), "asgineer.run() server arg must be a string."
    assert isinstance(bind, str), "asgineer.run() bind arg must be a string."
    assert ":" in bind, "asgineer.run() bind arg must be 'host:port'"
    bind = bind.replace("localhost", "127.0.0.1")

    # Select server function
    try:
        func = SERVERS[server.lower()]
    except KeyError:
        raise ValueError(f"Invalid server specified: {server!r}")

    # Delegate
    return func(appname, bind, **kwargs)


def _run_hypercorn(appname, bind, **kwargs):
    from hypercorn.__main__ import main

    # Hypercorn docs say: "Hypercorn has two loggers, an access logger and an error logger.
    # By default neither will actively log." So we dont need to do anything.

    kwargs["bind"] = bind

    args = [f"--{key.replace('_', '-')}={str(val)}" for key, val in kwargs.items()]
    return main(args + [appname])


def _run_uvicorn(appname, bind, **kwargs):
    from uvicorn.main import main

    if ":" in bind:
        host, _, port = bind.partition(":")
        kwargs["host"] = host
        kwargs["port"] = port
    else:
        kwargs["host"] = bind

    # Default to an error log_level, otherwise uvicorn is quite verbose
    kwargs.setdefault("log_level", "warning")

    args = [f"--{key.replace('_', '-')}={str(val)}" for key, val in kwargs.items()]
    return main(args + [appname])


def _run_daphne(appname, bind, **kwargs):
    from daphne.cli import CommandLineInterface

    if ":" in bind:
        host, _, port = bind.partition(":")
        kwargs["bind"] = host
        kwargs["port"] = port
    else:
        kwargs["bind"] = bind

    # Default to warning level verbosity
    # levelmap = {"error": 0, "warn": 0, "warning": 0, "info": 1, "debug": 2}
    kwargs.setdefault("verbosity", 0)

    args = [f"--{key.replace('_', '-')}={str(val)}" for key, val in kwargs.items()]
    return CommandLineInterface().run(args + [appname])


SERVERS = {"hypercorn": _run_hypercorn, "uvicorn": _run_uvicorn, "daphne": _run_daphne}
