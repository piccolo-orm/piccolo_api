Endpoints
=========

If using Piccolo as a backend, there is an endpoint for logging in, which will
return a token.

-------------------------------------------------------------------------------

token_login
-----------

This creates an endpoint for logging in, and getting a token.

.. code-block:: python

    from piccolo_api.token_auth.endpoints import token_login
    from starlette import Starlette
    from starlette.routing import Route, Router


    app = Starlette(
        routes=[
            Route("/login/", token_login()),
        ]
    )

For the user to login you **have to create a token for the user** in the
``TokenAuth`` table (the easiest way is to create token in ``Piccolo Admin``).

Usage
~~~~~

You can use any HTTP client to get the token. In our example we use ``curl``.

To get a token:

.. code-block:: shell

    curl -X POST \
        -H "Content-Type: application/json"
        -d '{"username": "piccolo", "password": "piccolo123"}' \
        http://localhost:8000/login/


To get data from a protected endpoint:

.. code-block:: shell

    curl -H "Authorization: Bearer your-token" \
        http://localhost:8000/private/movies/

.. hint:: You can use all HTTP methods by passing a valid token to the ``Authorization`` header.


Source
~~~~~~

.. currentmodule:: piccolo_api.token_auth.endpoints

.. autoclass:: token_login

.. autoclass:: PiccoloTokenProvider

.. autoclass:: TokenProvider
