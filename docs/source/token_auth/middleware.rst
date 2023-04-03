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
~~~~~~~~~~~~~~~~~~~~~~~

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

If successful a user called `secret_token_user` is added to the scope.

This provider is useful for protecting internal services, where the client is
trusted not to leak the tokens.

It is also useful for protecting login endpoints when accessed from native
apps. The client provides the token to be able to access the login endpoint,
after which they obtain a unique token, which is used to authenticate with
other endpoints.

PiccoloTokenAuthProvider
~~~~~~~~~~~~~~~~~~~~~~~~

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
