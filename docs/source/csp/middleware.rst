CSPMiddleware
=============

CSP (Content Security Policy) middleware signals to a browser to only execute
scripts which have come from the same domain. This provides some defence
against cross site scripting.

.. code-block:: python

    from piccolo_api.csp.middleware import CSPMiddleware

    wrapped_asgi_app = CSPMiddleware(asgi_app)

    import uvicorn
    uvicorn.run(wrapped_asgi_app)
