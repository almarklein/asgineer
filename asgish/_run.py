"""
This module implements a ``run()`` function to start an ASGI server of choice.
"""


def run(app, server, bind="localhost:8080", *, log_level="info", **kwargs):
    """ Programatic API to run the given ASGI app with the given ASGI server.
    (This works for any ASGI app, not just Asgish apps.)
    
    Arguments:
    
    * app (required): The ASGI application object, or a string ``"module.path:appname"``.
    * server (required): The name of the server library to use, e.g. uvicorn/hypercorn/etc.
    * log_level: The logging level, e.g. warning/info/debug. Default 'info'.
    * kwargs: additional arguments to pass to the underlying server library.
    """

    # Compose application name
    if isinstance(app, str):
        appname = app
        if ":" not in appname:
            raise ValueError("If specifying an app by name, give its full path!")
    else:
        appname = app.__module__ + ":" + app.__name__

    # Check server and bind
    assert isinstance(server, str), "asgish.run() server arg must be a string."
    assert isinstance(bind, str), "asgish.run() bind arg must be a string."
    assert ":" in bind, "asgish.run() bind arg must be 'host:port'"
    bind = bind.replace("localhost", "127.0.0.1")

    # Select server function
    try:
        func = SERVERS[server.lower()]
    except KeyError:
        raise ValueError(f"Invalid server specified: {server!r}")

    # Delegate
    return func(appname, bind, log_level, **kwargs)


def _run_hypercorn(appname, bind, log_level, **kwargs):
    from hypercorn.__main__ import main

    kwargs["bind"] = bind
    # kwargs['log_level'] = log_level

    args = [f"--{key.replace('_', '-')}={str(val)}" for key, val in kwargs.items()]
    return main(args + [appname])


def _run_uvicorn(appname, bind, log_level, **kwargs):
    from uvicorn.main import main

    if ":" in bind:
        host, _, port = bind.partition(":")
        kwargs["host"] = host
        kwargs["port"] = port
    else:
        kwargs["host"] = bind

    kwargs["log_level"] = log_level

    args = [f"--{key.replace('_', '-')}={str(val)}" for key, val in kwargs.items()]
    return main(args + [appname])


def _run_daphne(appname, bind, log_level, **kwargs):
    from daphne.cli import CommandLineInterface

    if ":" in bind:
        host, _, port = bind.partition(":")
        kwargs["bind"] = host
        kwargs["port"] = port
    else:
        kwargs["bind"] = bind

    levelmap = {"error": 0, "warn": 0, "warning": 0, "info": 1, "debug": 2}
    kwargs["verbosity"] = levelmap[log_level.lower()]

    args = [f"--{key.replace('_', '-')}={str(val)}" for key, val in kwargs.items()]
    return CommandLineInterface().run(args + [appname])


SERVERS = {"hypercorn": _run_hypercorn, "uvicorn": _run_uvicorn, "daphne": _run_daphne}
