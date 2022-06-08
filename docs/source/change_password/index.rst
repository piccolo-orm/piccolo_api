Change user password
====================

change_password
---------------

Endpoint where the authenticated user can change the password. If you send a GET request to 
this endpoint, a simple form is shown in which the user can change the password manually.

.. image:: images/change_password.png

.. hint::
    You can use a custom template, which matches the look and feel of your
    application. See the ``template_path`` parameter.

Alternatively, you can change password programatically by sending a POST
request to this endpoint (passing in ``old_password``, ``new_password`` and
``confirm_password`` parameters as JSON, or as form data).

When the password change is successful, the user is redirected to the login endpoint
and has to log in again because with password changes we invalidate the session cookie.

.. warning:: 
    Only authenticated users can change their passwords!

Examples
~~~~~~~~

Here's a Starlette example:

.. code-block:: python

    from piccolo_api.change_password.endpoints import change_password
    from piccolo_api.session_auth.middleware import SessionsAuthBackend
    from starlette import Starlette
    from starlette.middleware.authentication import AuthenticationMiddleware

    app = Starlette(
        routes=[
            Mount(
                "/change-password/",
                AuthenticationMiddleware(
                    change_password(),
                    SessionsAuthBackend(),
                ),
            ),
        ],
    )

Here's a FastAPI example:

.. code-block:: python

    from fastapi import FastAPI
    from piccolo_api.change_password.endpoints import change_password
    from piccolo_api.session_auth.middleware import SessionsAuthBackend
    from starlette.middleware.authentication import AuthenticationMiddleware

    app = FastAPI(
        routes=[
            Mount(
                "/change-password/",
                AuthenticationMiddleware(
                    change_password(),
                    SessionsAuthBackend(),
                ),
            ),
        ],
    )


Source
~~~~~~

.. currentmodule:: piccolo_api.change_password.endpoints

.. autofunction:: change_password
