.. Asgish documentation master file, created by
   sphinx-quickstart on Wed Sep 26 15:13:51 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the Asgish documentation!
====================================

`Asgish <https://asgish.readthedocs.io/>`_ is a tool to write asynchronous
web applications, using as few abstractions as possible, while still
offering a friendly API. It does not do fancy routing; it's async
handlers all the way down.

More precisely, Asgish is a Python ASGI web microframework. You don't
need to know what ASGI is, but if you want to know more, :doc:`read here <asgi>`.

Cool stuff:

* Since Asgish does not depend on ``asyncio``, it can also be used with alternative
  async libraries like `Trio <https://github.com/python-trio/trio>`_.
* When running Asgish on `Uvicorn <https://github.com/encode/uvicorn>`_, it is one
  of the fastest web frameworks available (it should be faster than Sanic).
* You can write your web app with Asgish, and switch the underlying (ASGI) server
  without having to change your code.
* Asgi is so small that it fits in the palm of your hand!


.. toctree::
    :maxdepth: 1
    :caption: Contents:

    start
    usage
    reference
    asgi
