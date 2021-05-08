..  _SessionAuth:

Session Auth
============

Introduction
------------

Session auth is the classic approach to authentication on the web. When a user
logs in, a session cookie is set on their browser, which contains a unique
session ID. This session ID is also stored by the server in a
database. Each time the user makes a request, the session ID stored in the
cookie is compared with the ones stored in the database, to check if the user
has a valid session.

There are several advantages to session auth:

 * A session can be invalidated at any time, by deleting a session from the database.
 * HTTP-only cookies are immune to tampering with Javascript.

-------------------------------------------------------------------------------

Tables
------

You need somewhere to store session tokens, and also somewhere to store user
credentials.

You can add ``piccolo_api.session_auth.piccolo_app`` to the ``apps`` arguments
of the ``AppRegistry`` in ``piccolo_conf.py``.

.. code-block:: bash

    APP_REGISTRY = AppRegistry(
        apps=[
            ...
            "piccolo_api.session_auth.piccolo_app",
            ...
        ]
    )

To learn more about Piccolo apps, see the `Piccolo docs <https://piccolo-orm.readthedocs.io/en/latest/piccolo/projects_and_apps/index.html>`_.

To run the migrations and create the tables, run:

.. code-block:: bash

    piccolo migrations forwards user
    piccolo migrations forwards session_auth

You can also choose to manually create the tables if you prefer.

-------------------------------------------------------------------------------

Endpoints
---------

The endpoints are designed to integrate with an ASGI app, such as Starlette.

For an example of how it all hangs together, you can see `Piccolo admin <https://github.com/piccolo-orm/piccolo_admin>`_,
as it uses session auth.

session_login
~~~~~~~~~~~~~

This checks the username and password provided by the user, and if correct,
creates a new session.

.. code-block:: python

    from piccolo_api.session_auth.endpoints import session_login

    login_endpoint = session_login()

It's recommended to protect any login endpoints with rate limiting middleware
(see :ref:`RateLimiting`), to help slow down any brute force attacks.

session_logout
~~~~~~~~~~~~~~

This unsets the cookie value, and invalidates the session in the database.

.. code-block:: bash

    from piccolo_api.session_auth.endpoints import session_logout

    logout_endpoint = session_logout()

-------------------------------------------------------------------------------

Middleware
----------

You can protect any endpoints using the ``SessionsAuthBackend``.

.. code-block:: python

    from starlette.middleware.authentication import AuthenticationMiddleware

    from piccolo_api.session_auth.middleware import SessionsAuthBackend


    app = AuthenticationMiddleware(
        my_asgi_app,
        backend=SessionsAuthBackend(),
    )

.. currentmodule:: piccolo_api.session_auth.middleware

.. autoclass:: SessionsAuthBackend
