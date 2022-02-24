Piccolo API
===========

Piccolo API makes it easy to turn your `Piccolo ORM <https://piccolo-orm.readthedocs.io/en/latest/>`_
tables into a working REST API, using ASGI.

It also includes a bunch of essential middleware for building a production
ASGI app, covering authentication, security, and more.

.. toctree::
   :caption: CRUD
   :maxdepth: 1

   ./crud/index
   ./fastapi/index

.. toctree::
   :caption: OpenAPI
   :maxdepth: 1

   ./openapi/index

.. toctree::
   :caption: Security
   :maxdepth: 1

   ./csp/index
   ./csrf/index
   ./rate_limiting/index

.. toctree::
   :caption: Authentication
   :maxdepth: 1

   ./jwt/index
   ./session_auth/index
   ./token_auth/index
   ./advanced_auth/index

.. toctree::
   :caption: Contributing
   :maxdepth: 1

   ./contributing/index

.. toctree::
   :caption: Changes
   :maxdepth: 1

   ./changes/index
