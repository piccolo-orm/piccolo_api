Endpoints
=========

An endpoint is provided for JWT login, and is designed to integrate with an
ASGI app, such as Starlette or FastAPI.

-------------------------------------------------------------------------------

jwt_login
---------

This creates an endpoint for logging in, and getting a JSON Web Token (JWT).

.. code-block:: python

    from piccolo_api.jwt_auth.endpoints import jwt_login
    from starlette import Starlette
    from starlette.routing import Route, Router


    app = Starlette(
        routes=[
            Route(
                path="/login/",
                endpoint=jwt_login(
                    secret='mysecret123'
                )
            ),
        ]
    )

secret
~~~~~~

This is used for signing the JWT.

expiry
~~~~~~

An optional argument, which allows you to control when a token expires. By
default it's set to 1 day.

.. code-block:: python

    from datetime import timedelta

    jwt_login(
        secret='mysecret123',
        expiry=timedelta(minutes=10)
    )

.. hint:: You generally want short expiry tokens for web applications, and
   longer expiry times for mobile applications.

.. hint:: See :class:`JWTMiddleware <piccolo_api.jwt_auth.middleware.JWTMiddleware>`
    for how to protect your endpoints.

-------------------------------------------------------------------------------

Usage
-----

You can use any HTTP client to get the JWT token. In our example we use ``curl``.

To get a JWT token:

.. code-block:: shell

    curl -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "piccolo", "password": "piccolo123"}' \
        http://localhost:8000/login/


To get data from a protected endpoint:

.. code-block:: shell

    curl -H "Authorization: Bearer your-JWT-token" \
        http://localhost:8000/private/movies/

.. hint:: You can use all ``HTTP`` methods by passing a valid JWT token in the ``Authorization`` header.

-------------------------------------------------------------------------------

Source
------

.. currentmodule:: piccolo_api.jwt_auth.endpoints

.. autofunction:: jwt_login
