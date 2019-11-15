jwt_login
=========

This creates an endpoint for logging in, and getting a JSON Web Token (JWT).

.. code-block:: python

    from starlette.routing import Route, Router
    from piccolo_api.jwt_auth.endpoints import jwt_login

    from settings import SECRET


    asgi_app = Router([
        Route(
            path="/login/",
            endpoint=jwt_login(
                secret=SECRET
            )
        ),
    ])

    import uvicorn
    uvicorn.run(asgi_app)

Required arguments
------------------

You have to pass in two arguments:

* auth_table - a subclass of Piccolo's ``BaseUser`` class, which is used to
  authenticate the user.
* secret - this is used for signing the JWT.

expiry
------

An optional argument, which allows you to control when a token expires. By
default it's set to 1 day.

.. code-block:: python

    from datetime import timedelta

    jwt_login(
        secret=SECRET,
        expiry=timedelta(minutes=10)
    )

.. hint:: You generally want short expiry tokens for web applications, and
   longer expiry times for mobile applications.

.. hint:: See :ref:`JWTMiddleware` for how to protect your endpoints.
