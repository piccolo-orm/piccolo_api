Welcome to Piccolo API's documentation!
=======================================

Piccolo API makes it easy to turn your `Piccolo ORM <https://piccolo-orm.readthedocs.io/en/latest/>`_
tables into a working REST API, using ASGI.

It also includes a bunch of essential middleware for building a production
ASGI app, covering authentication, security, and more.


CRUD
----

.. toctree::
   :maxdepth: 1

   ./crud/index
   ./fastapi/index

Security
--------

.. toctree::
   :maxdepth: 1

   ./csp/index
   ./csrf/index
   ./rate_limiting/index

Authentication
--------------

.. toctree::
   :maxdepth: 1

   ./jwt/index
   ./session_auth/index
   ./token_auth/index

Changes
-------

.. toctree::
   :maxdepth: 1

   ./changes/index
