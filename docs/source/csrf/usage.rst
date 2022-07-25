Usage
=====

Setup
-----

Using the middleware is straightforward. You can wrap your ASGI app in it:

.. code-block:: python

    from piccolo_api.csrf.middleware import CSRFMiddleware

    app = CSRFMiddleware(my_asgi_app, allowed_hosts=["foo.com"])

Or you can pass it to the middleware argument of your ASGI app. For example,
with FastAPI:

.. code-block:: python

    from fastapi import FastAPI
    from starlette.middleware import Middleware

    app = FastAPI(middleware=[Middleware(CSRFMiddleware)])

Or Starlette:

.. code-block:: python

    from starlette import Starlette
    from starlette.middleware import Middleware

    app = Starlette(middleware=[Middleware(CSRFMiddleware)])

-------------------------------------------------------------------------------

How it works
------------

When the user makes a request, the middleware makes sure that a CSRF cookie is
set on their device. This cookie contains a random token.

When a request is made with a non-safe method (e.g. POST), then the middleware
checks for the cookie, and the token contained within the cookie either in a
HTTP header or form field. If the token values don't match, the request is
rejected.

**Note: You have to explicitly tell the middleware to look for the token in a
form field:**

.. code-block:: python

    app = CSRFMiddleware(my_asgi_app, allow_form_param=True)

It isn't enabled by default, as adding it to the header is preferable (see
below).

-------------------------------------------------------------------------------

Accessing the CSRF token in HTML
--------------------------------

As mentioned, you need to add the token contained within the CSRF cookie as a
HTTP header or form field. There are two ways of accessing this value.

Template variable
~~~~~~~~~~~~~~~~~

Firstly, we can get the ``csrftoken`` value from the requests' ASGI scope, and
then insert it into the template context:

.. code-block:: python

    def my_endpoint(request: Request):
        csrftoken = request.scope.get('csrftoken')
        csrf_cookie_name = request.scope.get('csrf_cookie_name')

        template = ENVIRONMENT.get_template("example.html.jinja")
        content = template.render(
            csrftoken=csrftoken,
            csrf_cookie_name=csrf_cookie_name
        )

        return HTMLResponse(content)

And then within the HTML template:

.. code-block:: html

    <form method="POST">
        <label>Username</label>
        <input type="text" name="username" />
        <label>Password</label>
        <input type="password" name="password" />

        {% if csrftoken and csrf_cookie_name %}
            <input type="hidden" name="{{ csrf_cookie_name }}">{{ csrtoken }}</input>
        {% endif %}

        <button>Login</button>
    </form>

Reading from the cookie
~~~~~~~~~~~~~~~~~~~~~~~

Rather than injecting the CSRF token into the template, we can read it directly
from the cookie, using something like `js-cookie <https://github.com/js-cookie/js-cookie>`_.

.. code-block:: html

    <script src="https://cdnjs.cloudflare.com/ajax/libs/js-cookie/2.2.1/js.cookie.min.js"></script>

    <script>
    var csrftoken = Cookies.get('csrftoken');
    </script>

Full example
~~~~~~~~~~~~

In the the example below, we get the token from the cookie, and add it to the
request header.

.. code-block:: html

    <form method="POST" onsubmit="login(event,this)">
        <label>Username</label>
        <input type="text" name="username" />
        <label>Password</label>
        <input type="password" name="password" />

        <button>Login</button>
    </form>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/js-cookie/2.2.1/js.cookie.min.js"></script>

    <script>
        function login(event, form) {
            const csrftoken = Cookies.get('csrftoken');
            event.preventDefault()
            fetch("/login/", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": csrftoken,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ username: form.username.value, password: form.password.value })
            })
        }
    </script>

-------------------------------------------------------------------------------

Should I embed the token in the form, or add it as a HTTP header?
-----------------------------------------------------------------

Setting the cookie in the header is preferable as:

* It makes caching easier, as CSRF tokens aren't embedded in HTML forms.
* We no longer have to worry about BREACH attacks.

However, you can embed the CSRF token in the form if you want.

.. code-block:: python

    app = CSRFMiddleware(my_asgi_app, allow_form_param=True)

To guard against BREACH attacks, you can use rate limiting middleware on that
endpoint, or just disable HTTP compression for your website.

-------------------------------------------------------------------------------

Source
------

.. automodule:: piccolo_api.csrf.middleware
    :members:
