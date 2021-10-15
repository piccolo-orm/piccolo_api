Tables
======

You need somewhere to store session tokens, and also somewhere to store user
credentials.

You can add ``piccolo_api.session_auth.piccolo_app`` to the ``apps`` arguments
of the ``AppRegistry`` in ``piccolo_conf.py``.

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

You can also choose to manually create the tables if you prefer.
