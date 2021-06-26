OpenAPI
=======

Introduction
------------

Several ASGI frameworks generate an OpenAPI schema for you, by looking at the
type annotations for your endpoints (for example, FastAPI and BlackSheep).

Piccolo API ships with an endpoint which renders the Swagger UI, for interacting
with the OpenAPI schema. It provides some extra configuration options which
makes it work well with Piccolo middleware (such as CSRF).

.. automodule:: piccolo_api.openapi.endpoints
    :members:
