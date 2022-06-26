Commands
========

If you've registered the ``audit_logs`` app in your ``piccolo_conf.py`` file
(see the :ref:`migrations docs <AuditLogMigrations>`), it gives you access to a
custom command.

clean
-----

If you run the following on the command line, it will delete all logs
from the database.

.. code-block:: bash

    piccolo audit_logs clean
