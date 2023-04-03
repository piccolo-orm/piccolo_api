Tables
======

We store the tokens in :class:`TokenAuth <piccolo_api.token_auth.tables.TokenAuth>` table,
and the user credentials in :class:`BaseUser <piccolo.apps.user.tables.BaseUser>` table.

-------------------------------------------------------------------------------

.. _TokenMigrations:

Migrations
----------

We recommend creating these tables using migrations.

You can add ``piccolo_api.token_auth.piccolo_app`` to the ``apps`` arguments
of the :class:`AppRegistry <piccolo.conf.apps.AppRegistry>` in ``piccolo_conf.py``.

.. code-block:: bash

    APP_REGISTRY = AppRegistry(
        apps=[
            ...
            "piccolo_api.token_auth.piccolo_app",
            "piccolo.apps.user.piccolo_app",
            ...
        ]
    )

To learn more about Piccolo apps, see the `Piccolo docs <https://piccolo-orm.readthedocs.io/en/latest/piccolo/projects_and_apps/index.html>`_.

To run the migrations and create the tables, run:

.. code-block:: bash

    piccolo migrations forwards user
    piccolo migrations forwards token_auth

-------------------------------------------------------------------------------

Creating them manually
----------------------

If you prefer not to use migrations, and want to create them manually, you can
do this instead:

.. code-block:: python

    from piccolo_api.token_auth.tables import TokenAuth
    from piccolo.apps.user.tables import BaseUser
    from piccolo.tables import create_tables

    create_tables(BaseUser, TokenAuth, if_not_exists=True)

-------------------------------------------------------------------------------

Source
------

TokenAuth
~~~~~~~~~

.. currentmodule:: piccolo_api.token_auth.tables

.. autoclass:: TokenAuth
    :class-doc-from: class
    :members: create_token, create_token_sync, get_user_id, authenticate, authenticate_sync,
    :undoc-members: 
    :member-order: groupwise
