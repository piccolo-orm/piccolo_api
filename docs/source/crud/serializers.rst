Serializers
===========

``PiccoloCRUD`` uses `Pydantic <https://github.com/samuelcolvin/pydantic>`_
internally to serialize and deserialize data.

create_pydantic_model
---------------------

By using ``create_pydantic_model`` we can very easily create a `Pydantic model <https://pydantic-docs.helpmanual.io/usage/models/>`_
from a Piccolo ``Table``.

When using ``PiccoloCRUD``, you don't have to worry about this - it's all
handled internally. However, ``create_pydantic_model`` is very useful when
integrating Piccolo with a framework such as `FastAPI <https://github.com/tiangolo/fastapi>`_,
which also uses Pydantic for serialisation.

Source
~~~~~~

.. automodule:: piccolo_api.crud.serializers
    :members:

FastAPI template
~~~~~~~~~~~~~~~~

To create a new FastAPI app using Piccolo, simply use:

.. code-block:: bash

    piccolo asgi new

This uses ``create_pydantic_model`` to create serializers.

See the `Piccolo ASGI docs <https://piccolo-orm.readthedocs.io/en/latest/piccolo/asgi/index.html>`_
for details.
