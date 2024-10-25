===============
Getting started
===============


Installation
============

To install or upgrade, run:

.. code-block:: shell

    $ pip install -U asgineer


Dependencies
============

Asgineer does not directly depend on any other libraries, but it
does need an ASGI erver to run on. You need to install one
of these seperately:

* `Uvicorn <https://github.com/encode/uvicorn>`_ is bloody fast (thanks to uvloop and httptools).
* `Hypercorn <https://gitlab.com/pgjones/hypercorn>`_ can be multi-process (uses h11 end wsproto).
* `Daphne <https://github.com/django/daphne>`_ is part of the Django ecosystem (uses Twisted).
* `Trio-web <https://github.com/sorcio/trio-asgi>`_ is based on Trio, pre-alpa and incomplete, you can help improve it!
* Others will surely come, also watch `this list <https://asgi.readthedocs.io/en/latest/implementations.html#servers>`_ ...
