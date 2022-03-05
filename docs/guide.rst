==============
Asgineer guide
==============


A first look
============

Here's an example web application written with Asgineer:

.. code-block:: python

    # example.py
    import asgineer
    
    @asgineer.to_asgi
    async def main(request):
        return f"<html>You requested <b>{request.path}</b></html>"


Responses are return values
===========================

An HTTP response consists of three things: an integer
`status code <https://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_,
a dictionary of `headers <https://en.wikipedia.org/wiki/List_of_HTTP_header_fields>`_,
and the response `body <https://en.wikipedia.org/wiki/HTTP_message_body>`_.

In the above example, Asgineer sets the appropriate status code and
headers so that the browser will render the result as a web page. In the
:doc:`reference docs <reference>` the rules are explained.

You can also provide both headers and body, or all three values:

.. code-block:: python

   async def main(request):
        return 200, {}, f"<html>You requested <b>{request.path}</b></html>"


Running the application
=======================

Asgineer provides a ``run()`` function that is aware of the most common
ASGI servers. Just put this at the bottom of the same file to enable
running the file as a script:

.. code-block:: python
    
    if __name__ == '__main__':  
        asgineer.run('uvicorn', main, 'localhost:8080')
        # or use 'hypercorn', 'daphne', ...

Alternatively, the above example can be run from the command line, using
any ASGI server:

.. code-block:: shell
    
    # Uvicorn:
    $ uvicorn example.py:main --host=localhost --port=8080
    # Hypercorn:
    $ hypercorn example.py:main --bind=localhost:8080
    # Daphne:
    $ daphne example:main --bind=localhost --port=8080


Routing
=======

Asgineer takes a "linear" approach to handling request. It avoids magic
like routing systems, so you can easily follow how requests move through
your code. To do the routing, make your main handler delegate to
sub-handlers:

.. code-block:: python

    import asgineer

    ASSETS = {
        'main.js': (
            b"console.log('Hello from asgineer!')",
            'application/javascript'
        )
    }


    @asgineer.to_asgi
    async def main(request):
        path = request.path
        if path == '/':
            return (
                "<html>"
                '  <script src="/assets/main.js"></script>'
                "  Index page"
                "</html>"
            )
        elif path.startswith('/assets/'):
            return await asset_handler(request)
        elif path.startswith('/api/'):
            return await api_handler(request)
        else:
            return 404, {}, 'Page not found'


    async def asset_handler(request):
        fname = request.path.split('/assets/')[-1]
        if fname in ASSETS:
            body, content_type = ASSETS[fname]
            return {'content-type': content_type}, body
        else:
            return 404, {}, 'asset not found'


    async def api_handler(request):
        path = request.path.split('/api/')[-1]
        return {'path': path}


For the common task of serving assets, Asgineer provides an easy way to do this
correct and fast, with :func:`.make_asset_handler`.


A lower level way to send responses 
===================================

The initial example can also be written using lower level mechanics. Note that
Asgineer does not automatically set headers in this case:

.. code-block:: python

   async def main(request):
        await request.accept(200, {"content-type": "text/html"})
        await request.send("<html>You requested {request.path}</html>")

This approach is intended for connections with a longer lifetime, such as
chuncked responses, long polling, and server-side events (SSE).
E.g. a chuncked response:
    
.. code-block:: python

   async def main(request):
        await request.accept(200, {"content-type": "text/plain"})
        async for chunk in some_generator():
            await request.send(chunk)


Websockets
==========

Websocket handlers are written in a similar way:

.. code-block:: python
    
    async def websocket_handler(request):
        await request.accept()
        
        # Wait for one message, which can be str or bytes
        m = await request.receive()
        
        # Send a message, which can be str, bytes or dict
        await request.send('Hello!')
        
        # Iterate over incoming messages until the connection closes
        async for msg in request.receive_iter():
            await msg.send('echo ' + str(msg))
        
        # Note: the connection is automatically closed when the handler returns


----

Read the :doc:`reference docs <reference>` to read more about the details.
