Token Auth
==========

Introduction
------------

Token auth is a simple approach to authentication, which is most suitable for
mobile apps and embedded systems.

Each user / client has a token generated for them. The token is just a random
string - no information is embedded within it, as is the case with JWT.

When a client makes a request, the token needs to be added as a header. The
user object associated with this token is then retrieved from a
`TokenAuthProvider`. By default, this is a Piccolo table, but you can implement
your own token provider if you so choose.

The token doesn't expire. It's suitable for mobile apps and other systems where
tokens can be securely stored on the device. The client logic is simple to
implement, as you don't have to worry about refreshing your token.

It's not recommended to use this type of authentication with web apps, because
you can't securely store the token using Javascript, which makes it
susceptible to exposure using a XSS attack.

Header format
-------------

The client has to make a request which includes the `Authorization` HTTP
header, with a value of `Bearer SOMETOKEN`.

Middleware
----------

The middleware builds upon Starlette's `AuthenticationMiddleware`.

`TokenAuthBackend` is used to extract the token from the request. If the token
is present and correct, then the request is accepted and the corresponding user
is added to the scope, otherwise it is rejected.

`TokenAuthBackend` can work with several different `TokenAuthProvider`
subclasses. The following are provided by default, but custom ones can be
written by creating your own `TokenAuthProvider` subclasses.

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
        SecretTokenAuthProvider,
    )

    app = AuthenticationMiddleware(
        my_asgi_app,
        backend=PiccoloTokenAuthProvider(),
    )

You'll have to run the migrations for this to work correctly.

Endpoints
---------

If using Piccolo as a backend, there is an endpoint for logging in, which will
return a token.
