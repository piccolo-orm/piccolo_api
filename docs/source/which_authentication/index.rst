Which auth to use?
==================

Piccolo API provides easy-to-use middleware and endpoints for implementing
authentication in your ASGI applications.

To learn more about how ASGI works, see the `Introduction to ASGI <https://piccolo-orm.com/blog/introduction-to-asgi/>`_
article on the Piccolo blog. FastAPI and Starlette are examples of ASGI frameworks.

For most web apps, we recommend using :ref:`Session Auth <SessionAuth>`. It is
robust, and well understood. Piccolo API has a very complete implementation with
endpoints for logging in, logging out, changing password, and more.

:ref:`Token Auth <TokenAuth>` is useful when authenticating mobile apps, or
machine to machine communication.

:ref:`JWTAuth` has emerged in recent years as an alternative to session auth.
Rather than storing a session in a database and using cookies, it uses signed
tokens instead. If you application requires JWT, then we have basic support
for it, but we recommend :ref:`Session Auth <SessionAuth>` for most
applications.
