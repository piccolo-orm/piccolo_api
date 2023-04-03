Which auth to use?
==================

Middleware is a type of computer software that sits between the 
operating system and the applications that run on it.
`Introduction to ASGI <https://piccolo-orm.com/blog/introduction-to-asgi/>`_ 
is a nice article on the Piccolo blog to learn more about the asgi ecosystem.

Piccolo API provides a set of easy-to-use asgi middlewares that you can use
to implement authentication for your asgi applications.

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
