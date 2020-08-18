# Asgineer
A really thin ASGI web framework 🐍🤘

[![Build Status](https://api.travis-ci.org/almarklein/asgineer.svg)](https://travis-ci.org/almarklein/asgineer)
[![Documentation Status](https://readthedocs.org/projects/asgineer/badge/?version=latest)](https://asgineer.readthedocs.io/?badge=latest)
[![Package Version](https://badge.fury.io/py/asgineer.svg)](https://pypi.org/project/asgineer)


## Introduction

[Asgineer](https://asgineer.readthedocs.io) is a tool to write asynchronous
web applications, using as few abstractions as possible, while still
offering a friendly API. The
[guide](https://asgineer.readthedocs.io/guide.html) and
[reference](https://asgineer.readthedocs.io/reference.html) take just a few
minutes to read!

When running Asgineer on [Uvicorn](https://github.com/encode/uvicorn),
it is one of the fastest web frameworks available. It supports http
long polling, server side events (SSE), and websockets. And has utilities
to serve assets the right (and fast) way.


## Example

```py
# example.py

import asgineer

@asgineer.to_asgi
async def main(request):
    return f"<html>You requested <b>{request.path}</b></html>"

if __name__ == '__main__':
    asgineer.run(main, 'uvicorn', 'localhost:8080')
```

You can start the server by running this script, or start it the *ASGI way*, e.g.
with Uvicorn:
```
$ uvicorn example:main --host=localhost --port=8080
```

## Installation and dependencies

Asgineer needs Python 3.6 or higher. To install or upgrade, run:
```
$ pip install -U asgineer
```

Asgineer has zero hard dependencies, but it
needs an ASGI server to run on, like
[Uvicorn](https://github.com/encode/uvicorn),
[Hypercorn](https://gitlab.com/pgjones/hypercorn), or
[Daphne](https://github.com/django/daphne).


## Development

Extra dev dependencies: `pip install invoke pytest pytest-cov black flake8 requests websockets`

Run `invoke -l` to get a list of dev commands, e.g.:

* `invoke autoformat` to apply Black code formatting.
* `invoke lint` to test for unused imports and more.
* `invoke tests` to run the tests, optionally set the `ASGI_SERVER` environment variable.


## License

BSD 2-clause.
