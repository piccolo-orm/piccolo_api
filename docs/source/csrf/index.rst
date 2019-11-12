CSRF
====

Introduction
------------

CSRF (Cross Site Request Forgery) is a serious security vulnerability for
websites which are relying on cookies for authentication.

Browsers will send cookies belonging to a domain, no matter which website the
request was made from. So if you're authenticated on foo.com, an attacker can
make malicious HTTP requests to foo.com on your behalf even when you're
browsing a completely different website.

Prevention Measures
-------------------

There are many approaches to `preventing CSRF <https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html>`_.
The security measures implemented by this middleware are:

Double submit cookie
~~~~~~~~~~~~~~~~~~~~

A cookie is set on the user's browser, containing a random token.

When submitting unsafe requests (POST, DELETE, PUT etc.), this token also needs
to be added to the request using the ``X-CSRFToken`` header. The backend
verifies that the token in the header matches the token in the cookie.

The Same Origin Policy means that cookies from one domain can't be read or set
from another domain. This means an attacker doesn't know what the token value
is.

.. warning:: The limitation of this approach is sub domains can set cookies on
  the root domain. For example, a.foo.com can create cookies on foo.com. If
  you have a secure website on foo.com, be aware of this attack vector. It's
  highly recommended not to give access to sub domains to any untrusted third
  parties.

Also, the Same Origin Policy prevents websites from setting custom headers
when making AJAX requests to other domains. In theory just adding a custom
header should be sufficient without the need for a token, but some people
have been able to `circumvent it <https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#use-of-custom-request-headers>`_
in the past. A developer could also accidentally disable this protection using
`CORS <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Allow-Headers>`_,
by allowing custom headers from other domains, which is why a token is also
required.

Most popular AJAX libraries make setting this custom header very straight
forward.

Referer checking
~~~~~~~~~~~~~~~~

When running under HTTPS - which you 100% should be doing in production, then
most browsers send ``origin`` and / or ``referer`` headers (`source <https://seclab.stanford.edu/websec/csrf/csrf.pdf>`_).

This is used to detect if requests are coming from a different domain.

Make sure safe methods are safe!
--------------------------------

The CSRF protection only works on unsafe methods - DELETE, POST, PUT etc.

Make sure that safe methods (e.g. GET) are indeed safe, meaning they do not
cause state to change (i.e. adding data to the database, or other side
effects).

Same Origin Cookies
-------------------

This is a relatively new feature designed to prevent CSRF attacks, which is
already supported by most evergreen browsers. If all browsers supported it,
there would be no need for any of the other CSRF preventions outlined above,
but until then we employ a defence in depth strategy, and use a combination
of prevention strategies to protect older browsers.

The session cookies provided by Piccolo API are same origin.

Usage
-----

Using the middleware is straight forward.

.. code-block:: python

    from piccolo_api.csrf.middleware import CSRFMiddleware
    from starlette.exceptions import ExceptionMiddleware


    # A basic ASGI app
    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send({"type": "http.response.body", "body": b"Hello, world!"})


    # Wrap it in middleware:
    APP = ExceptionMiddleware(
        CSRFMiddleware(app, allowed_hosts=["foo.com"])
    )

You'll notice we also have to wrap the app in Starlette's
``ExceptionMiddleware``.

What about non-AJAX requests?
-----------------------------

Currently, this CSRF protection requires a header to be set, meaning it
requires Javascript to make the request using AJAX.

There are some benefits to this approach:

 * It makes caching easier, as CSRF tokens aren't embedded in HTML forms.
 * We no longer have to worry about BREACH attacks.

Support for CSRF tokens embedded in HTML forms might be added in the future.
