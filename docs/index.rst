.. Asgineer documentation master file, created by
   sphinx-quickstart on Wed Sep 26 15:13:51 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the Asgineer documentation!
======================================

`Asgineer <https://asgineer.readthedocs.io/>`_ is a tool to write asynchronous
web applications, using as few abstractions as possible, while still
offering a friendly API. There is no fancy routing; you write an async
request handler, and delegate to other handlers as needed.

More precisely, Asgineer is a (thin) Python ASGI web microframework.


Cool stuff:

* When running on `Uvicorn <https://github.com/encode/uvicorn>`_, Asgineer is one
  of the fastest web frameworks available.
* Asgineer has great support for chunked responses, long polling, server
  side events (SSE), and websockets.
* Asgineer has utilities to help you serve your assets the right (and fast) way.
* You can write your web app with Asgineer, and switch the underlying (ASGI) server
  without having to change your code.
* Great test coverage.
* Asgineer is so small that it fits in the palm of your hand!


.. toctree::
    :maxdepth: 2
    :caption: Contents:

    start
    guide
    reference
    testutils
    asgi
    Examples ↪<https://github.com/almarklein/asgineer/tree/main/examples>
