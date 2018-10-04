================
Asgish reference
================

This page contains the API documentation of Asgish' functions and classes,
as well as a description of Asgish more implicit API.


The functions
=============

.. autofunction:: asgish.handler2asgi

.. autofunction:: asgish.run


How to return a response
========================

An HTTP response consists of three things: an integer
`status code <https://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_,
a dictionary of `headers <https://en.wikipedia.org/wiki/List_of_HTTP_header_fields>`_,
and the response `body <https://en.wikipedia.org/wiki/HTTP_message_body>`_.
Many web frameworks wrap these up in a response object. In Asgish you
just return them. You can also return just the body, or the body and
headers; these are all equivalent:

.. code-block:: python

    return 200, {}, 'hello'
    return {}, 'hello'
    return 'hello'

In the end, the body of an HTTP response is always binary, but Asgish handles some common cases for you:

* A ``bytes`` object is passed unchanged.
* A ``str`` object that starts with ``<!DOCTYPE html>`` or ``<html>`` is UTF-8 encoded,
  and the ``content-type`` header defaults to ``text/html``.
* Any other ``str`` object is UTF-8 encoded,
  and the ``content-type`` header defaults to ``text/plain``.
* A ``dict`` object is JSON-encoded,
  and the ``content-type`` header is set to ``application/json``.

Responses can also be send in chunks by returning an async generator (which
must yield ``bytes`` or ``str`` objects). Asgish will use the generator to stream
the body to the client:

.. code-block:: python
    
    async def chunkgenerator():
        for chunk in ['foo', 'bar', 'spam', 'eggs']:
            # ... do work or async sleep here ...
            yield chunk
    
    async def handler(request):
        return 200, {}, chunkgenerator()


The Request classes
===================

.. autoclass:: asgish.BaseRequest
    :members:

.. autoclass:: asgish.HttpRequest
    :members:

.. autoclass:: asgish.WebsocketRequest
    :members:


Details on Asgish' behavior
===========================

Asgish will invoke your main handler for each incoming request. If an
exception is raised inside the handler, this exception will be logged
using the logger that can be obtained with
``logging.getLogger("asgish")``, which by default writes to stderr. A
status 500 (internal server error) response is send back, and the error
message is included (if possible).

Similarly, when the returned response is flawed, a (slightly different)
error message is logged and included in the response.

In fact, Asgish handles all exceptions, since the ASGI servers log
errors in differt ways (some just ignore them). If an error does fall
through, it can be considered a bug.
