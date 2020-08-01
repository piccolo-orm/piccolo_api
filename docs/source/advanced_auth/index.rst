Advanced Auth
=============

Multiple Auth Backends
----------------------

Sometimes you'll want to use multiple auth backends to protect the same
endpoints. An example is using :ref:`SessionAuth` for web users and
:ref:`TokenAuth` for mobile app users.

You can do this using ``AuthenticationBackendJunction`` which wraps multiple
``AuthenticationBackend`` subclasses, and tries each in turn. If none of
them successfully authenticate, than authentication fails.

.. code-block:: python

    from piccolo_api.session_auth.middleware import SessionsAuthBackend
    from piccolo_api.shared.auth.junction import AuthenticationBackendJunction
    from piccolo_api.token_auth.middleware import (
        TokenAuthBackend,
        SecretTokenAuthProvider,
    )
    from starlette.middleware.authentication import AuthenticationMiddleware


    app = AuthenticationMiddleware(
        my_asgi_app,
        backend=AuthenticationBackendJunction(
            backends=[
                SessionsAuthBackend(),
                TokenAuthBackend(
                    SecretTokenAuthProvider(tokens=["abc123"])
                )
            ],
        )
    )
