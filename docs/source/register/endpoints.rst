Endpoints
=========

register
--------

An endpoint for registering a user. If you send a GET request to this endpoint,
a simple registration form is rendered, where a user can manually sign up.

.. image:: images/register_template.png

.. hint::
    You can use a custom template, which matches the look and feel of your
    application. See the ``template_path`` parameter.

Alternatively, you can register a user programatically by sending a POST
request to this endpoint (passing in ``username``, ``email``, ``password`` and
``confirm_password`` parameters as JSON, or as form data).

When registration is successful, the user can be redirected to a login endpoint.
The destination can be configured using the ``redirect_to`` parameter.

Examples
~~~~~~~~

Here's a Starlette example:

.. code-block:: python

    from piccolo_api.session_auth.endpoints import register
    from starlette import Starlette

    app = Starlette()

    app.mount('/register/', register(redirect_to="/login/"))

Here's a FastAPI example:

.. code-block:: python

    from piccolo_api.session_auth.endpoints import register
    from fastapi import FastAPI

    app = FastAPI()

    app.mount('/register/', register(redirect_to="/login/"))

Source
~~~~~~

.. currentmodule:: piccolo_api.register.endpoints

.. autofunction:: register
