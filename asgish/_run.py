"""
This module implements a ``run()`` function to start an ASGI server of choice.
"""


def run(app, server, *, bind="127.0.0.1:8080", log_level="info", **kwargs):

    # alphabet = 'abcdefghijklmnopqrstuvwxyz'
    # name = app.__name__ + '_' + ''.join(random.choice(alphabet) for i in range(7))
    # globals()[name] = app
    appname = app.__module__ + ":" + app.__name__

    servers = {
        "hypercorn": _run_hypercorn,
        "uvicorn": _run_uvicorn,
        "daphne": _run_daphne,
    }

    try:
        func = servers[server.lower()]
    except KeyError:
        raise ValueError(f"Invalid server specified: {server}")

    # return func(__name__ + ':' + name, bind, log_level, **kwargs)
    return func(appname, bind, log_level, **kwargs)


def _run_hypercorn(appname, bind, log_level, **kwargs):
    import hypercorn
    from hypercorn.__main__ import main

    kwargs["bind"] = bind
    # kwargs['log_level'] = log_level

    args = [f"--{key.replace('_', '-')}={str(val)}" for key, val in kwargs.items()]
    return main(args + [appname])


def _run_uvicorn(appname, bind, log_level, **kwargs):
    import uvicorn
    from uvicorn.main import main

    if ":" in bind:
        host, _, port = bind.partition(":")
        kwargs["host"] = host
        kwargs["port"] = port
    else:
        kwargs["host"] = bind

    args = [f"--{key.replace('_', '-')}={str(val)}" for key, val in kwargs.items()]
    return main(args + [appname])


def _run_daphne(appname, bind, log_level, **kwargs):
    import daphne
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
