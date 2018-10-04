# Asgish
A really thin ASGI web framework 🐍🤘

[![Build Status](https://api.travis-ci.org/almarklein/asgish.svg)](https://travis-ci.org/almarklein/asgish)
[![Documentation Status](https://readthedocs.org/projects/asgish/badge/?version=latest)](https://asgish.readthedocs.io/?badge=latest)
[![Package Version](https://badge.fury.io/py/asgish.svg)](https://pypi.org/project/asgish)
    

## Introduction

[Asgish](https://asgish.readthedocs.io) is a tool to write asynchronous
web applications, using as few abstractions as possible, while still
offering a friendly API. There is no fancy routing; you write an async
request handler, and delegate to other handlers as needed.

When running asgish on [Uvicorn](https://github.com/encode/uvicorn),
it is one of the fastest web frameworks available.


## Example

```py
# example.py

from asgish import handler2asgi

@handler2asgi
async def main(request):
    return f"<html>You requested <b>{request.path}</b></html>"

if __name__ == '__main__':
    from asgish import run
    run(main, 'uvicorn', 'localhost:8080')
```

You can start the server by running this script, or start it the "ASGI way", e.g.
with Uvicorn:
```
$ uvicorn example:main --host=localhost --port=8080
```

## Installation and dependencies

Asgish need Python 3.6 or higher. To install or upgrade, run:
```
$ pip install asgish --upgrade
```

Asgish does not directly depend on any other libraries, but it
does need an ASGI erver to run on, like
[Uvicorn](https://github.com/encode/uvicorn),
[Hypercorn](https://gitlab.com/pgjones/hypercorn), or
[Daphne](https://github.com/django/daphne).


## Development

Extra dev dependencies: `pip install pytest pytest-cov black pyflakes requests autobahn`

* Use `black .` to apply Black code formatting.
* Run `pyflakes .` to test for unused imports and more.
* Run `pytest tests` to run the tests, optionally set the `ASGISH_SERVER` environment variable.


## License

BSD 2-clause.
