JWT
===

Introduction
------------

JWT is a token format, often used for authentication.

jwt_login
---------

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
~~~~~~~~~~~~~~~~~~

You have to pass in two arguments:

* auth_table - a subclass of Piccolo's ``BaseUser`` class, which is used to
  authenticate the user.
* secret - this is used for signing the JWT.

expiry
~~~~~~

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

.. hint:: See ``JWTMiddleware`` for how to protect your endpoints.


JWTMiddleware
-------------

This wraps an ASGI app, and ensures a valid token is passed in the header.
Otherwise a 403 error is returned. If the token is valid, the corresponding
``user_id`` is added to the ``scope``.

blacklist
~~~~~~~~~

Optionally, you can pass in a ``blacklist`` argument, which is a subclass of
``JWTBlacklist``. The implementation of the ``in_blacklist`` method is up to
the user - the data could come from a database, a file, a Python list, or
anywhere else.

.. code-block:: python

    # An example blacklist.

    BLACKLISTED_TOKENS = ['abc123', 'def456']


    class MyBlacklist(JWTBlacklist):

        async def in_blacklist(self, token: str) -> bool:
            return token in BLACKLISTED_TOKENS


    asgi_app = JWTMiddleware(
        my_endpoint,
        auth_table=User,
        secret=SECRET,
        blacklist=MyBlacklist()
    )

.. hint:: Blacklists are important if you have tokens with a long expiry date.

.. todo - show example POST using requests
