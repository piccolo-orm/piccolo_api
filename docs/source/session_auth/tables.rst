Tables
======

We store the session tokens in :class:`SessionsBase <piccolo_api.session_auth.tables.SessionsBase>`,
and the user credentials in :class:`BaseUser <piccolo.apps.user.tables.BaseUser>`.

-------------------------------------------------------------------------------

.. _SessionMigrations:

Migrations
----------

We recommend creating these tables using migrations.

You can add ``piccolo_api.session_auth.piccolo_app`` to the ``apps`` arguments
of the :class:`AppRegistry <piccolo.conf.apps.AppRegistry>` in ``piccolo_conf.py``.

.. code-block:: bash

    APP_REGISTRY = AppRegistry(
        apps=[
            ...
            "piccolo_api.session_auth.piccolo_app",
            "piccolo.apps.user.piccolo_app",
            ...
        ]
    )

To learn more about Piccolo apps, see the `Piccolo docs <https://piccolo-orm.readthedocs.io/en/latest/piccolo/projects_and_apps/index.html>`_.

To run the migrations and create the tables, run:

.. code-block:: bash

    piccolo migrations forwards user
    piccolo migrations forwards session_auth

-------------------------------------------------------------------------------

Creating them manually
----------------------

If you prefer not to use migrations, and want to create them manually, you can
do this instead:

.. code-block:: python

    from piccolo_api.session_auth.tables import SessionsBase
    from piccolo.apps.user.tables import BaseUser
    from piccolo.tables import create_tables

    create_tables(BaseUser, SessionsBase, if_not_exists=True)

-------------------------------------------------------------------------------

Source
------

SessionsBase
~~~~~~~~~~~~

.. currentmodule:: piccolo_api.session_auth.tables

.. autoclass:: SessionsBase
