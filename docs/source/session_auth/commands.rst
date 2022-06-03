Commands
========

If you've registered the ``session_auth`` app in your ``piccolo_conf.py`` file
(see the :ref:`migrations docs <SessionMigrations>`), it gives you access to a
custom command.

clean
-----

If you run the following on the command line, it will delete any old sessions
from the database.

.. code-block:: bash

    piccolo session_auth clean
