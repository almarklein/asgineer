=============
What is ASGI?
=============

*You don't have to know or care about ASGI in order to use Asgish,
but here's a short summary.*

The `ASGI <https://asgi.readthedocs.io>`_ specification allows async web
servers and frameworks to talk to each-other in a standardized way. You can select
a framework (like Asgish, Quart, Starlette, etc.) based on how you want to write
your code, and you select a server (like Uvicorn, Hypercorn, Daphne) based on how
fast/reliable/secure you want it to be.

ASGI is Like WSGI, but for async.

In particular, the main part of an ASGI application looks something like this:
    
.. code-block:: python

    class Application:
    
        def __init__(self, scope):
            self.scope = scope
    
        async def __call__(self, receive, send):
            ...


ASGI is great, but writing web apps directly in ASGI format is silly.
Asgish is a tiny layer on top. It's so minimal that it still feels a
bit like ASGI, but nicer. Thus the name Asgish (ASGI-ish).

Other ASGI frameworks include
`Starlette <https://github.com/encode/starlette>`_,
`Quart <https://github.com/pgjones/quart>`_, and
`others <https://asgi.readthedocs.io/en/latest/implementations.html#application-frameworks>`_.
