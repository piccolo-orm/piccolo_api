Full Example
============

Let's combine all of previous examples into a complete app.

-------------------------------------------------------------------------------

FastAPI
-------

.. include:: ./examples/example.py
    :code: python

-------------------------------------------------------------------------------

Starlette
---------

Is almost identical to the FastAPI example - just replace ``FastAPI`` with
``Starlette``, and use Starlette's ``HTTPEndpoint`` for your endpoints.
You also need to  write your own crud endpoints because ``Starlette`` 
can't use ``FastAPIWrapper``. An example is in `SessionAuth <https://piccolo-api.readthedocs.io/en/latest/session_auth/example.html>`_.
