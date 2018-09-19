# asgish
An ASGI web framework with an ASGI-ish API


## A quick look

Write a simple web application using minimal abstractions:

```py

from asgish import handler2asgi

@handler2asgi
async def main(request):
    return 200, {'content-type': 'text/html'}, f"You requested <b>{request.path}</b>"

```

Then run from the command line:
```
$ uvicorn example.py:main
```

You can replace `uvicorn` with any other ASGI server, like `hypercorn` or `daphne`.

Some servers also allow running programatically. Just put this at the bottom of
the same file:

```py
...

import uvicorn
uvicorn.run(main)

```

## Details

With asgish you build your web application completely with async
handlers. There is no smart routing or other fancy stuff. This means
there is less to learn.

Each http response really consists of three things, an integer
[status code](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes),
a dictionary of [headers](https://en.wikipedia.org/wiki/List_of_HTTP_header_fields),
and the response body. In asgish you just return these three. You can also
omit the status and/or headers. These are all equivalent:
    
```py
return 200, {}, 'hello'
return 200, 'hello'
return {}, 'hello'
return 'hello'
```

The body of an http response is always binary. In asgish, a string or
dict body is automatically converted, and the content-type is set to
'text/plain' and 'application/json', respectively.

Responses can also be send in chunks, using an async generator:
```
async def chunkgenerator():
    for chunk in ['foo', 'bar', 'spam', 'eggs']:
        yield chunk

async def handler(request):
    return 200, {}, chunkgenerator()
```


## The request object

<!-- begin Request docs -->


<!-- end Request docs -->


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
