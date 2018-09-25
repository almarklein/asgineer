"""
This module implements a ``run()`` function to start an ASGI server of choice,
and a matching CLI function.
"""

import sys


def run(app, *, server=None, bind="127.0.0.1:8080", log_level="info", **kwargs):
    """ Programatic API to start an ASGI server.
    
    Arguments:
       app: The ASGI application object.
       server: The name of the server library to use, e.g. 'uvicorn', 'hypercorn', 'daphne'.
       log_level: The logging level, e.g. 'warning', 'info', 'debug'.
       kwargs: additional arguments to pass to the underlying server library.
    
    """

    # Compose application name
    appname = app.__module__ + ":" + app.__name__

    # Check server and bind
    assert server and isinstance(
        server, str
    ), "asgish.run() server arg must be given and a string."
    assert bind and ":" in bind, "asgish.run() bind arg must be 'host:port'"
    bind = bind.replace("localhost", "127.0.0.1")

    # Select server function
    try:
        func = SERVERS[server.lower()]
    except KeyError:
        raise ValueError(f"Invalid server specified: {server}")

    # Delegate
    return func(appname, bind, log_level, **kwargs)


def main(argv):
    """ CLI API to start an ASGI server. The arguments match those of the ``run()``
    function (underscores in arguments names are dashes in the CLI).
    """

    # Parse args, collect into kwargs and positional args
    argv2 = []
    kwargs = {}
    argv = argv.copy()
    while argv:
        arg = argv.pop(0)
        if arg.startswith("--"):
            if "=" in arg:
                key, _, val = arg[2:].partition("=")
            else:
                key = arg[2:]
                val = argv.pop(0, "")
            kwargs[key] = val
        else:
            argv2.append(arg)

    # Extract required args (--server and --bind)
    try:
        server = kwargs.pop("server")
    except KeyError:
        raise RuntimeError("Asgish command needs --server=xx")
    try:
        bind = kwargs.pop("bind")
    except KeyError:
        raise RuntimeError("Asgish command needs --bind=host:port")
    assert ":" in bind, "Asgish command needs --bind=host:port"
    bind = bind.replace("localhost", "127.0.0.1")

    # Extract special optional args
    log_level = kwargs.pop("log-level", "info")

    # Extract application name from positional args
    if len(argv2) != 1:
        raise RuntimeError(
            f"Asgish command expects one positional argument, got: {argv2}"
        )
    appname = argv2[0]

    # Select server function
    try:
        func = SERVERS[server.lower()]
    except KeyError:
        raise ValueError(f"Invalid server specified: {server}")

    # Delegate
    func(appname, bind, log_level, **kwargs)


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

if __name__ == "__main__":
    main(sys.argv[1:])
