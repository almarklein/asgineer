=================
How to use Asgish
=================

Asgish tries to add a minimal amount of abstractions. If you know that
``asgish.handler2asgi()`` turns an async function into an ASGI app,
what the given request object looks like, and how to return the
response, you know all there is to know about Asgish.


A first look
============

Here's an example web application written with Asgish:

.. code-block:: python

    # example.py
    from asgish import handler2asgi
    
    @handler2asgi
    async def main(request):
        return f"<html>You requested <b>{request.path}</b></html>"


Running the application
=======================

Asgish provides a ``run()`` function that is aware of the most common
ASGI servers. Just put this at the bottom of the same file to enable
running the file as a script:

.. code-block:: python
    
    if __name__ == '__main__':  
        from asgish import run
        run('hypercorn', main, 'localhost:8080')
        # or use 'hypercorn', 'daphne', ...

Alternatively, the above example can be run from the command line, using
any ASGI server, e.g. with Uvicorn:

.. code-block:: shell

    $ uvicorn example.py:main --host=localhost --port=8080

... or Hypercorn:

.. code-block:: shell
    
    $ hypercorn example.py:main --bind=localhost:8080



Returning the response
======================

An HTTP response consists of three things: an integer
`status code <https://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_,
a dictionary of `headers <https://en.wikipedia.org/wiki/List_of_HTTP_header_fields>`_,
and the response `body <https://en.wikipedia.org/wiki/HTTP_message_body>`_.
Many web frameworks wrap these up in a response object.
In Asgish you just return them. You can
omit the status and/or headers, so these are all equivalent:
    
.. code-block:: python

    return 200, {}, 'hello'
    return 200, 'hello'
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


Websockets
==========

Websockets don't need a response. Instead, the request object can be used
to send and receive messages:


.. code-block:: python
    
    # Note; the websocket API is still under change
    async def websocket_handler(request):
        async for msg in request.read_iter():
            await msg.send('echo ' + msg)
        # The websocket connection is closed when this handler returns


The request object
==================

Your handler functions will be passed a ``request`` object. read the
:doc:`reference docs <reference>` to see what this object looks like.
