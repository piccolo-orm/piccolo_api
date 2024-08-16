Endpoints
=========

You must mount these ASGI endpoints in your app.

.. currentmodule:: piccolo_api.mfa.endpoints

``mfa_setup``
-------------------------

.. autofunction:: mfa_setup

``session_login``
-----------------

Make sure you pass the ``mfa_providers`` argument to
:func:`session_login <piccolo_api.session_auth.endpoints.session_login>`,
so it knows to look for an MFA token.
