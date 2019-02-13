==================
Asgineer reference
==================

This page contains the API documentation of Asgineer's functions and classes,
as well as a description of Asgineer more implicit API.


The functions
=============

.. autofunction:: asgineer.to_asgi

.. autofunction:: asgineer.run


How to return a response
========================

An HTTP response consists of three things: an integer
`status code <https://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_,
a dictionary of `headers <https://en.wikipedia.org/wiki/List_of_HTTP_header_fields>`_,
and the response `body <https://en.wikipedia.org/wiki/HTTP_message_body>`_.
Many web frameworks wrap these up in a response object. In Asgineer you
just return them. You can also return just the body, or the body and
headers; these are all equivalent:

.. code-block:: python

    return 200, {}, 'hello'
    return {}, 'hello'
    return 'hello'

If needed, the :func:`.normalize_response` function can be used to
turn a response (e.g. of a subhandler) into a 3-element tuple.
In the end, the body of an HTTP response is always binary, but Asgineer
handles some common cases for you:

* A ``bytes`` object is passed unchanged.
* A ``str`` object that starts with ``<!DOCTYPE html>`` or ``<html>`` is UTF-8 encoded,
  and the ``content-type`` header defaults to ``text/html``.
* Any other ``str`` object is UTF-8 encoded,
  and the ``content-type`` header defaults to ``text/plain``.
* A ``dict`` object is JSON-encoded,
  and the ``content-type`` header is set to ``application/json``.

Responses can also be send in chunks by returning an async generator (which
must yield ``bytes`` or ``str`` objects). Asgineer will use the generator to stream
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

.. autoclass:: asgineer.BaseRequest
    :members:

.. autoclass:: asgineer.HttpRequest
    :members:

.. autoclass:: asgineer.WebsocketRequest
    :members:


Details on Asgineer's behavior
==============================

Asgineer will invoke your main handler for each incoming request. If an
exception is raised inside the handler, this exception will be logged
(including ``exc_info``) using the logger that can be obtained with
``logging.getLogger("asgineer")``, which by default writes to stderr. A
status 500 (internal server error) response is sent back, and the error
message (without traceback) is included (if the response has not yet been sent).

Similarly, when the returned response is flawed, a (slightly different)
error message is logged and included in the response.

In fact, Asgineer handles all exceptions, since the ASGI servers log
errors in different ways (some just ignore them). If an error does fall
through, it can be considered a bug.


Utility functions
=================

The ``asgineer.utils`` module provides a few utilities for common tasks.

.. autofunction:: asgineer.utils.normalize_response

.. autofunction:: asgineer.utils.make_asset_handler
