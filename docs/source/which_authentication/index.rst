Which auth to use?
==================

For most web apps, we recommend using :ref:`session auth <SessionAuth>`. It is
robust, and well understood. Piccolo API has a very complete implementation with
endpoints for logging in, logging out, changing password, and more.

:ref:`Token auth <TokenAuth>` is useful when authenticating mobile apps, or
machine to machine communication.

:ref:`JWT` has emerged in recent years as an alternative to session auth.
Rather than storing a session in a database and using cookies, it uses signed
tokens instead. If you application requires JWT, then we have basic support
for it, but we recommend :ref:`session auth <SessionAuth>` for most
applications.
