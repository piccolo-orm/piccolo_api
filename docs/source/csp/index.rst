CSP
===

CSP (Content Security Policy) middleware signals to a browser to only execute
scripts which have come from the same domain. This provides some defence
against cross site scripting.

Usage
-----

.. code-block:: python

    from piccolo_api.csp.middleware import CSPMiddleware

    app = CSPMiddleware(my_asgi_app)
