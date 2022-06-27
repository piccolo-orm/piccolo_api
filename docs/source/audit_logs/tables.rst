Tables
======

``audit_logs`` is a ``Piccolo`` app that records changes made by users to database tables.
We store the audit logs in :class:`AuditLog <piccolo_api.audit_logs.tables.AuditLog>`.

-------------------------------------------------------------------------------

.. _AuditLogMigrations:

Migrations
----------

We recommend creating the ``audit_logs`` tables using migrations.

You can add ``piccolo_api.audit_logs.piccolo_app`` to the ``apps`` arguments
of the :class:`AppRegistry <piccolo.conf.apps.AppRegistry>` in ``piccolo_conf.py``.

.. code-block:: bash

    APP_REGISTRY = AppRegistry(
        apps=[
            ...
            "piccolo_api.audit_logs.piccolo_app",
            ...
        ]
    )

To learn more about Piccolo apps, see the `Piccolo docs <https://piccolo-orm.readthedocs.io/en/latest/piccolo/projects_and_apps/index.html>`_.

To run the migrations and create the table, run:

.. code-block:: bash

    piccolo migrations forwards audit_logs

-------------------------------------------------------------------------------

Creating them manually
----------------------

If you prefer not to use migrations, and want to create them manually, you can
do this instead:

.. code-block:: python

    from piccolo_api.audit_logs.tables import AuditLog
    from piccolo.tables import create_db_tables_sync

    create_db_tables_sync(AuditLog, if_not_exists=True)

-------------------------------------------------------------------------------

Source
------

AuditLog
~~~~~~~~

.. currentmodule:: piccolo_api.audit_logs.tables

.. autoclass:: AuditLog
    :members:
