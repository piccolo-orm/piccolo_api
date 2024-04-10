.. _SessionAuthMiddleware:

Middleware
==========

This middleware protects endpoints using session cookies.

-------------------------------------------------------------------------------

Setup
-----

The middleware wraps your ASGI app.

Here's a Starlette example:

.. code-block:: python

    from starlette import Starlette
    from starlette.middleware.authentication import AuthenticationMiddleware
    from piccolo_api.session_auth.middleware import SessionsAuthBackend

    my_asgi_app = Starlette()

    app = AuthenticationMiddleware(
        my_asgi_app,
        backend=SessionsAuthBackend(),
    )

Here's a FastAPI example:


.. code-block:: python

    from fastapi import FastAPI
    from starlette.middleware.authentication import AuthenticationMiddleware
    from piccolo_api.session_auth.middleware import SessionsAuthBackend

    my_asgi_app = FastAPI()

    app = AuthenticationMiddleware(
        my_asgi_app,
        backend=SessionsAuthBackend(),
    )

On each request, the middleware looks for a session token held in a cookie,
and whether a corresponding user is found in the database. If so, a
``user`` object is added to the ASGI scope.

-------------------------------------------------------------------------------

Accessing user
--------------

In Starlette you can access the user in your endpoint using ``request.user``
or ``request.scope['user']``.

.. code-block:: python

    from starlette.requests import Request
    from starlette.endpoints import HTTPEndpoint
    from starlette.responses import JSONResponse

    class PostsEndpoint(HTTPEndpoint):
        async def get(self, request: Request):
            piccolo_user = request.user.user
            posts = await Post.select().where(
                Post.author.id == piccolo_user.id
            ).run()
            return JSONResponse(posts)


In FastAPI, you can also access the user from the request scope, as
follows:

.. code-block:: python

    from fastapi.requests import Request
    from fastapi.responses import JSONResponse

    @app.get('/posts/')
    def get_posts(request: Request):
        piccolo_user = request.user.user
        posts = await Post.select().where(
            Post.author.id == piccolo_user.id
        ).run()
        return JSONResponse(posts)

-------------------------------------------------------------------------------

``excluded_paths``
------------------

This works identically to token auth - see :ref:`excluded_paths`.

-------------------------------------------------------------------------------

Source
------

.. currentmodule:: piccolo_api.session_auth.middleware

SessionsAuthBackend
~~~~~~~~~~~~~~~~~~~

.. autoclass:: SessionsAuthBackend
