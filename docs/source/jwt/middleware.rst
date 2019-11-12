.. _JWTMiddleware:

JWTMiddleware
=============

This wraps an ASGI app, and ensures a valid token is passed in the header.
Otherwise a 403 error is returned. If the token is valid, the corresponding
``user_id`` is added to the ``scope``.

blacklist
---------

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