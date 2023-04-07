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
