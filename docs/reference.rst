==================
Asgineer reference
==================

This page contains the API documentation of Asgineer's functions and classes,
as well as a description of Asgineer more implicit API.


How to return a response
========================

An HTTP response consists of three things: a status code, headers, and the body.
Your handler must return these as a tuple. You can also return just the
body, or the body and headers; these are all equivalent:

.. code-block:: python

    return 200, {}, 'hello'
    return {}, 'hello'
    return 'hello'

If needed, the :func:`.normalize_response` function can be used to
turn a response (e.g. of a subhandler) into a 3-element tuple.

Asgineer automatically converts the body returned by your handler, and
sets the appropriate headers:

* A ``bytes`` object is passed unchanged.
* A ``str`` object that starts with ``<!DOCTYPE html>`` or ``<html>`` is UTF-8 encoded,
  and the ``content-type`` header defaults to ``text/html``.
* Any other ``str`` object is UTF-8 encoded,
  and the ``content-type`` header defaults to ``text/plain``.
* A ``dict`` object is JSON-encoded,
  and the ``content-type`` header is set to ``application/json``.
* An async generator can be provided as an alternative way to send a chunked response.

See :func:`request.accept <asgineer.HttpRequest.accept>` and :func:`request.send <asgineer.HttpRequest.send>`
for a lower level API (for which the auto-conversion does not apply).


Requests
========

.. autoclass:: asgineer.BaseRequest
    :members:

.. autoclass:: asgineer.HttpRequest
    :members:

.. autoclass:: asgineer.WebsocketRequest
    :members:

.. autoclass:: asgineer.RequestSet
    :members:

.. autoclass:: asgineer.DisconnectedError
    :members:


Entrypoint functions
====================

.. autofunction:: asgineer.to_asgi

.. autofunction:: asgineer.run



Utility functions
=================

The ``asgineer.utils`` module provides a few utilities for common tasks.

.. autofunction:: asgineer.utils.sleep

.. autofunction:: asgineer.utils.make_asset_handler

.. autofunction:: asgineer.utils.normalize_response

.. autofunction:: asgineer.utils.guess_content_type_from_body


Details on Asgineer's behavior
==============================

Asgineer will invoke your main handler for each incoming request. If an
exception is raised inside the handler, this exception will be logged
(including ``exc_info``) using the logger that can be obtained with
``logging.getLogger("asgineer")``, which by default writes to stderr.
If possible, a status 500 (internal server error) response is sent back
that includes the error message (without traceback).

Similarly, when the returned response is flawed, a (slightly different)
error message is logged and included in the response.

In fact, Asgineer handles all exceptions, since the ASGI servers log
errors in different ways (some just ignore them). If an error does fall
through, it can be considered a bug.
