============
Asgish guide
============


A first look
============

Here's an example web application written with Asgish:

.. code-block:: python

    # example.py
    import asgish
    
    @asgish.to_asgi
    async def main(request):
        return f"<html>You requested <b>{request.path}</b></html>"


Running the application
=======================

Asgish provides a ``run()`` function that is aware of the most common
ASGI servers. Just put this at the bottom of the same file to enable
running the file as a script:

.. code-block:: python
    
    if __name__ == '__main__':  
        asgish.run('uvicorn', main, 'localhost:8080')
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

To do your routing, check the request object and delegate to
other handlers:

.. code-block:: python

    import asgish
    
    @asgish.to_asgi
    async def main(request):
        path = request.path
        if path == '/':
            return f"<html>Index page</html>"
        elif path.startswith('/assets/'):
            return await asset_handler(request)
        elif path.startswith('/api/'):
            return await api_handler(request)
        else:
            return 404, {}, 'Page not found'
    
    async def asset_handler(request):
        fname = request.path.split('/assets/')[-1]
        if fname in ASSETS:
            body, content_type = ASEETS[fname]
            return {'content type': content_type}, body
        else:
            return 404, {}, 'asset not found'
    
    async def api_handler(request):
        path = request.path.split('/api/')[-1]
        return {'path', path}


Websockets
==========

Websocket handlers are written in a similar way, except that they should
not return a response. Instead, the request object can be used
to send and receive messages:

.. code-block:: python
    
    async def websocket_handler(request):
        
        # Wait for one message, which can be str or bytes
        m = await request.receive()
        
        # Send a message, which can be str, bytes or dict
        await request.send('Hello!')
        
        # Iterate over incoming messages until the connection closes
        async for msg in request.receive_iter():
            await msg.send('echo ' + str(msg))
        
        # Note: the websocket connection is closed when the handler returns


----

Read the :doc:`reference docs <reference>` to read more about the details.
