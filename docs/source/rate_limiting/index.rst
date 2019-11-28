Rate Limiting
=============

Introduction
------------

Rate limiting is useful for certain public API endpoints. Examples are:

 * Login endpoints - reducing the speed with which passwords can be brute forced.
 * Computationally intensive endpoints, which could lead to a DOS attack.

Usage
-----

.. code-block:: python

    from piccolo_api.rate_limiting.middleware import RateLimitingMiddleware
    from starlette.exceptions import ExceptionMiddleware

    app = ExceptionMiddleware(
        RateLimitingMiddleware(
            my_asgi_app
        )
    )

Providers
---------

The middleware can work with different `Providers`, which are responsible
for storing traffic data, and signalling when a rate limit has been exceeded.

By default ``InMemoryLimitProvider`` is used.

InMemoryLimitProvider
---------------------

Stores the traffic data in memory. You can customise it as follows:

.. code-block:: python

    app = ExceptionMiddleware(
        RateLimitingMiddleware(
            my_asgi_app,
            provider = InMemoryLimitProvider(
                limit=1000,
                timespan=300
            ),
        )
    )

The ``limit`` is the number of requests needed by a client within the
``timespan`` (measured in seconds) to trigger a 429 error (too many requests).

If you want a blocked client to be allowed access again after a time period,
specify this using the ``block_duration`` argument:

.. code-block:: python

    app = ExceptionMiddleware(
        RateLimitingMiddleware(
            my_asgi_app,
            provider = InMemoryLimitProvider(
                limit=1000,
                timespan=300,
                block_duration=300  # Blocked for 5 minutes
            ),
        )
    )

Custom Providers
----------------

A provider needs to implement a simple interface - see ``RateLimitProvider``.
Making provider is simple, if the built in ones don't meet your needs.
