Endpoints
=========

If using Piccolo as a backend, there is an endpoint for logging in, which will
return a token.

-------------------------------------------------------------------------------

TokenAuthLoginEndpoint
----------------------

This creates an endpoint for logging in, and getting a token.

.. code-block:: python

    from piccolo_api.token_auth.endpoints import TokenAuthLoginEndpoint
    from starlette import Starlette
    from starlette.routing import Route, Router


    app = Starlette(
        routes=[
            Route("/login/", TokenAuthLoginEndpoint),
        ]
    )

After creating login endpoint, you **have to create a token for the user** in the ``TokenAuth`` table 
(easiest way is to create token in ``Piccolo Admin``).

Usage
-----

You can use any HTTP client to get the token. In our example we use ``curl``

Get a token:

.. code-block:: shell

    curl -X POST -H "Content-Type: application/json" -d '{"username": "piccolo", "password": "piccolo123"}' http://localhost:8000/login/


Get data from a protected endpoint:

.. code-block:: shell

    curl -H "Authorization: Bearer your-token" http://localhost:8000/private/movies/

.. hint:: You can use all ``HTTP`` methods by passing valid token to the ``Authorization`` header.