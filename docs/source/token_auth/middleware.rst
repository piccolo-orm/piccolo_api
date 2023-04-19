Middleware
==========

The middleware builds upon Starlette's ``AuthenticationMiddleware``.

``TokenAuthBackend`` is used to extract the token from the request. If the token
is present and correct, then the request is accepted and the corresponding user
is added to the scope, otherwise it is rejected.

``TokenAuthBackend`` can work with several different ``TokenAuthProvider``
subclasses. The following are provided by default, but custom ones can be
written by creating your own ``TokenAuthProvider`` subclasses.

SecretTokenAuthProvider
-----------------------

This provider checks whether the token provided by the client matches a list of
predefined tokens.

.. code-block:: python

    from starlette.middleware.authentication import AuthenticationMiddleware

    from piccolo_api.token_auth.middleware import (
        TokenAuthBackend,
        SecretTokenAuthProvider,
    )

    app = AuthenticationMiddleware(
        my_asgi_app,
        backend=TokenAuthBackend(SecretTokenAuthProvider(tokens=["abc123"])),
    )

If successful a user called ``secret_token_user`` is added to the scope.

This provider is useful for protecting internal services, where the client is
trusted not to leak the tokens.

It is also useful for protecting login endpoints when accessed from native
apps. The client provides the token to be able to access the login endpoint,
after which they obtain a unique token, which is used to authenticate with
other endpoints.

PiccoloTokenAuthProvider
------------------------

This provider checks a Piccolo database table for a corresponding token, and
retrieves a matching user ID. It is the default provider.

.. code-block:: python

    from starlette.middleware.authentication import AuthenticationMiddleware

    from piccolo_api.token_auth.middleware import (
        TokenAuthBackend,
        PiccoloTokenAuthProvider,
    )

    app = AuthenticationMiddleware(
        my_asgi_app,
        backend=TokenAuthBackend(PiccoloTokenAuthProvider()),
    )

You'll have to run the migrations for this to work correctly.

-------------------------------------------------------------------------------

excluded_paths
~~~~~~~~~~~~~~

By default, if the token is invalid then the HTTP request is rejected.
However, by setting ``excluded_paths`` will allow the request
to continue on the endpoints specified in ``excluded_paths`` instead.

This is useful when using Swagger docs as they can be viewed in a browser,
but they are still token protected. If we want to communicate with endpoints, 
we need to set `FastAPI APIKeyHeader <https://github.com/tiangolo/fastapi/tree/master/fastapi/security>`_ as a dependency. After that we 
can authorize the user with a valid token as in the example below.

.. code-block:: python

    # An example usage of excluded_paths.

    from fastapi import Depends, FastAPI
    from fastapi.security.api_key import APIKeyHeader
    from home.tables import Movie  # An example Table
    from starlette.middleware.authentication import AuthenticationMiddleware
    from starlette.routing import Mount, Route

    from piccolo_api.crud.endpoints import PiccoloCRUD
    from piccolo_api.fastapi.endpoints import FastAPIKwargs, FastAPIWrapper
    from piccolo_api.token_auth.endpoints import token_login
    from piccolo_api.token_auth.middleware import (
        PiccoloTokenAuthProvider,
        TokenAuthBackend,
    )

    public_app = FastAPI(
        routes=[
            Route("/login/", token_login()),
        ],
    )


    auth_header = APIKeyHeader(name="Authorization")
    private_app = FastAPI(dependencies=[Depends(auth_header)])

    protected_app = AuthenticationMiddleware(
        private_app,
        backend=TokenAuthBackend(
            PiccoloTokenAuthProvider(),
            excluded_paths=["/docs", "/openapi.json"],
        ),
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

.. currentmodule:: piccolo_api.token_auth.middleware

.. autoclass:: PiccoloTokenAuthProvider

.. autoclass:: SecretTokenAuthProvider
