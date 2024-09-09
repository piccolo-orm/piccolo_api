Tables
======

``AuthenticatorSecret``
-----------------------

This is required by :class:`AuthenticatorProvider <piccolo_api.mfa.authenticator.provider.AuthenticatorProvider>`.

To create this table, you can using Piccolo's migrations.

Add ``piccolo_api.mfa.authenticator.piccolo_app`` to ``APP_REGISTRY`` in
``piccolo_conf.py``:

.. code-block:: python

    APP_REGISTRY = AppRegistry(
        apps=[
            "piccolo_api.mfa.authenticator.piccolo_app",
            ...
        ]
    )

Then run the migrations:

.. code-block:: bash

    piccolo migrations forwards mfa_authenticator

Alternatively, if not using Piccolo migrations, you can create the table
manually:

.. code-block:: pycon

    >>> from piccolo_api.mfa.authenticator.table import AuthenticatorProvider
    >>> AuthenticatorProvider.create_table().run_sync()
