=======================
Asgineer test utilities
=======================

When you've writting a fancy web application with Asgineer, you might want to
write some unit tests. The ``asgineer.testutils`` module provides some utilities
to help do that. It requires the ``requests`` library, and the ``websockets``
library when using websockets.


Testing example
===============

    
.. code-block:: python

    import json
    
    from asgineer.testutils import ProcessTestServer, MockTestServer
    
    
    # ----- Define handlers - you'd probably import these instead
    
    async def main_handler(request):
        if request.path.startswith('/api/'):
            return await api_handler(request)
        else:
            return "Hello world!"
    
    
    async def api_handler(request):
        return {'welcome': "This is a really silly API"}
    
    
    # ----- Test functions
    
    def test_my_app():
        
        with MockTestServer(api_handler) as p:
            r = p.get('/api/')
        
        assert r.status == 200
        assert "welcome" in json.loads(r.body.decode())
        
        
        with MockTestServer(main_handler) as p:
            r = p.get('')
        
        assert r.status == 200
        assert "Hello" in r.body.decode()
    
    
    if __name__ == '__main__':
        # Important: don't call the test functions from the root,
        # since this module gets re-imported!
        
        test_my_app()


Instead of the ``MockTestServer`` you can also use the
``ProcessTestServer`` to test with a real server like ``uvicorn``
running in a subprocess. The API is exactly the same though!


Test server classes
===================

.. autoclass:: asgineer.testutils.BaseTestServer
    :members:

.. autoclass:: asgineer.testutils.ProcessTestServer
    :members:

.. autoclass:: asgineer.testutils.MockTestServer
    :members:
