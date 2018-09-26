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
any ASGI server. E.g. Uvicorn:

.. code-block:: shell

    $ uvicorn example.py:main --host=localhost --port=8080

... or Hypercorn:

.. code-block:: shell
    
    $ hypercorn example.py:main --bind=localhost:8080



Returning the response
======================

With HTTP, a response really consists of three things: an integer
`status code <https://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_,
a dictionary of `headers <https://en.wikipedia.org/wiki/List_of_HTTP_header_fields>`_,
and the response `body <https://en.wikipedia.org/wiki/HTTP_message_body>`_.
In Asgish you just return these three. You can also
omit the status and/or headers. These are all equivalent:
    
.. code-block:: python

    return 200, {}, 'hello'
    return 200, 'hello'
    return {}, 'hello'
    return 'hello'

The body of an HTTP response is always binary. In Asgish the body can be:
    
* ``bytes``: is passed unchanged.
* ``str``: is UTF-8 encoded. When it starts with ``<!DOCTYPE html>`` or ``<html>`` the
  ``content-type`` header defaults to ``text/html``, otherwise it defaults to ``text/plain``.
* ``dict``: is JSON-encoded, and the ``content-type`` header is set to ``application/json``.
* an async generator: must yield ``bytes`` or ``str``,  see below.

Responses can also be send in chunks, using an async generator:

.. code-block:: python
    
    async def chunkgenerator():
        for chunk in ['foo', 'bar', 'spam', 'eggs']:
            yield chunk
    
    async def handler(request):
        return 200, {}, chunkgenerator()


The request object
==================

Your handler functions will be passed a ``request`` object. read the
:doc:`reference docs <reference>` to see what this object looks like.
