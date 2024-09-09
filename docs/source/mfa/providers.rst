Providers
=========

Most of the MFA code is fairly generic, but ``Providers`` implement the logic
which is specific to its particular authentication mechanism.

For example, ``AuthenticatorProvider`` knows how to authenticate tokens which
come from an authenticator app on a user's phone, and knows how to generate new
secrets which allow users to enable MFA.

.. currentmodule:: piccolo_api.mfa.provider

``MFAProvider``
---------------

.. autoclass:: MFAProvider

.. currentmodule:: piccolo_api.mfa.authenticator.provider

``AuthenticatorProvider``
-------------------------

.. autoclass:: AuthenticatorProvider
