.. _JWTMiddleware:

Middleware
==========

This middleware protects endpoints using JWT tokens.

-------------------------------------------------------------------------------

Setup
-----

``JWTMiddleware`` wraps an ASGI app, and ensures a valid token is passed in the header.
Otherwise a 403 error is returned. If the token is valid, the corresponding
``user_id`` is added to the ASGI ``scope``.

blacklist
~~~~~~~~~

Optionally, you can pass in a ``blacklist`` argument, which is a subclass of
:class:`JWTBlacklist`. The implementation of the ``in_blacklist`` method is up to
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
        secret='mysecret123',
        blacklist=MyBlacklist()
    )

.. hint:: Blacklists are important if you have tokens with a long expiry date.

allow_unauthenticated
~~~~~~~~~~~~~~~~~~~~~

By default, if the JWT token is invalid then the HTTP request is rejected.
However, by setting ``allow_unauthenticated=True`` the request will be allowed
to continue instead. The following will be added to the ASGI scope:

* ``user_id``, which is set to ``None``
* ``jwt_error``, explaining why the token is invalid
  (see :class:`JWTError <piccolo_api.jwt_auth.middleware.JWTError>`)

It is then up to the endpoints in your application to check whether ``user_id``
is ``None`` and then reject the request.

This is useful when the middleware is wrapping lots of endpoints, and you
want more control over which ones are protected, or want to take additional
actions when an error occurs before rejecting the request.

-------------------------------------------------------------------------------

visible_paths
~~~~~~~~~~~~~

By default, if the JWT token is invalid then the HTTP request is rejected.
However, by setting ``visible_paths`` will allow the request
to continue on the endpoints specified in ``visible_paths`` instead.

This is useful when using Swagger docs as they can be viewed in a browser,
but they are still token protected. If we want to communicate with endpoints, 
we need to set `FastAPI APIKeyHeader <https://github.com/tiangolo/fastapi/tree/master/fastapi/security>`_ as a dependency. After that we 
can authorize the user with a valid jwt token as in the example below.

.. code-block:: python

    # An example usage of visible_paths.

    from fastapi import Depends, FastAPI
    from fastapi.security.api_key import APIKeyHeader
    from home.tables import Movie  # An example Table
    from piccolo_api.jwt_auth.endpoints import jwt_login
    from piccolo_api.jwt_auth.middleware import JWTMiddleware
    from starlette.routing import Route

    public_app = FastAPI(
        routes=[
            Route(
                path="/login/",
                endpoint=jwt_login(
                    secret="mysecret123",
                    expiry=timedelta(minutes=60), 
                ),
            ),
        ],
    )


    auth_header = APIKeyHeader(name="Authorization")
    private_app = FastAPI(dependencies=[Depends(auth_header)])

    protected_app = JWTMiddleware(
        private_app,
        auth_table=BaseUser,
        secret="mysecret123",
        visible_paths=["/docs", "/openapi.json"],
    )


    FastAPIWrapper(
        "/movies/",
        fastapi_app=private_app,
        piccolo_crud=PiccoloCRUD(Movie, read_only=False),
        fastapi_kwargs=FastAPIKwargs(
            all_routes={"tags": ["Movie"]},
        ),
    )

    public_app.mount("/private", protected_app)

-------------------------------------------------------------------------------


Source
------

JWTMiddleware
~~~~~~~~~~~~~~

.. currentmodule:: piccolo_api.jwt_auth.middleware

.. autoclass:: JWTMiddleware

JWTBlacklist
~~~~~~~~~~~~

.. autoclass:: JWTBlacklist
    :members:

StaticJWTBlacklist
~~~~~~~~~~~~~~~~~~

.. autoclass:: StaticJWTBlacklist

JWTError
~~~~~~~~

.. autoclass:: JWTError
    :members:
    :undoc-members:
