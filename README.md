# asgish
An ASGI web framework with an ASGI-ish API

[![Build Status](https://api.travis-ci.org/almarklein/asgish.svg)](https://travis-ci.org/almarklein/asgish)


## Introduction

Asgish is a Python ASGI web microframework that tries to add as few
abstractions as possible, while still offering a friendly API. It does not
do fancy routing; it's async handlers all the way down.

The [ASGI](https://asgi.readthedocs.io) specification allows async web
servers and frameworks to talk to each-other in a standardized way.
Like WSGI, but for async.
I like getting to the metal, but writing web applications using
an [ASGI application class](https://asgi.readthedocs.io/en/latest/specs/main.html#applications)
is just too awkward, so I created this minimal layer on top.

Other ASGI frameworks include [Starlette](https://github.com/encode/starlette), [Quart](https://github.com/pgjones/quart),
and [others](https://asgi.readthedocs.io/en/latest/implementations.html#application-frameworks).


## A first look

```py
# example.py
from asgish import handler2asgi

@handler2asgi
async def main(request):
    return f"<html>You requested <b>{request.path}</b></html>"
```

## Running the application

The above example can be run from the command line:
```
$ uvicorn example.py:main
```

You can replace `uvicorn` with any other ASGI server, like `hypercorn` or `daphne`.

Some servers also allow running programatically. Just put this at the bottom of
the same file:

```py
import uvicorn
uvicorn.run(main)

```

## Returning the response

With HTTP, a response really consists of three things: an integer
[status code](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes),
a dictionary of [headers](https://en.wikipedia.org/wiki/List_of_HTTP_header_fields),
and the response [body](https://en.wikipedia.org/wiki/HTTP_message_body).
In asgish you just return these three. You can also
omit the status and/or headers. These are all equivalent:
    
```py
return 200, {}, 'hello'
return 200, 'hello'
return {}, 'hello'
return 'hello'
```

The body of an HTTP response is always binary. In asgish the body can be:
    
* `bytes`: is passed unchanged.
* `str`: is UTF-8 encoded. When it starts with '<!DOCTYPE ' or '<html>' the
  `content-type` header defaults to `text/html`, otherwise it defaults to `text/plain`.
* `dict`: is JSON-encoded, and the `content-type` header is set to `application/json`.
* an async generator: must yield bytes or str,  see below.

Responses can also be send in chunks, using an async generator:
```py
async def chunkgenerator():
    for chunk in ['foo', 'bar', 'spam', 'eggs']:
        yield chunk

async def handler(request):
    return 200, {}, chunkgenerator()
```


## API reference

<!-- begin docs -->
### class ``Request(scope, receive)``

Representation of an HTTP request. An object of this class is
passed to the request handler.

**``Request.scope``** - A dict representing the raw ASGI scope. See the
[ASGI reference](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope)
for details.

**``Request.method``** - The HTTP method (string). E.g. 'HEAD', 'GET', 'PUT', 'POST', 'DELETE'.

**``Request.headers``** - A dictionary representing the headers. Both keys and values are strings.

**``Request.url``** - The full (unquoted) url, composed of scheme, host, port,
path, and query parameters (string).

**``Request.scheme``** - The URL scheme (string). E.g. 'http' or 'https'.

**``Request.host``** - The server's host name (string).
See also ``scope['server']`` and ``scope['client']``.

**``Request.port``** - The server's port (integer).

**``Request.path``** - The path part of the URL (a string, with percent escapes decoded).

**``Request.querylist``** - A list with (key, value) tuples, representing the URL query parameters.

**``Request.querydict``** - A dictionary representing the URL query parameters.

**``Request.iter_body()``** - An async generator that iterates over the chunks in the body.

**``Request.get_body(limit=10485760)``** - Coroutine to get the bytes of the body.
If the end of the stream is not reached before the byte limit
is reached (default 10MiB), raises an IOError.

**``Request.get_json(limit=10485760)``** - Coroutine to get the body as a dict.
If the end of the stream is not reached before the byte limit
is reached (default 10MiB), raises an IOError.

### function ``handler2asgi(handler)``

Convert a request handler (a coroutine function) to an ASGI
application, which can be served with an ASGI server, such as
Uvicorn, Hypercorn, Daphne, etc.
<!-- end docs -->


## Installation and dependencies

Asgish need Python 3.6 or higher. It has no further dependencies except for
an ASGI server. Some possible servers:
    
* [uvicorn](https://github.com/encode/uvicorn)
* [hypercorn](https://gitlab.com/pgjones/hypercorn)
* [daphne](https://github.com/django/daphne)
* others will come ...

To install/upgrade: `pip install asgish --upgrade`


## Development

Extra dev dependencies: `pip install black pyflakes pytest sphinx`

* Use `black .` to apply Black code formatting.
* Run `pyflakes .` to test for unused imports and more.
* Run `python test_asgish.py --asgish_backend=xx` to run test, with `xx` 'uvicorn' or 'hypercorn'.
* Run `pytest .` to run the same test with pytest, optionally set the ASGISH_BACKEND encironment variable.


## License

BSD 2-clause.
