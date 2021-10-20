Serializers
===========

``PiccoloCRUD`` uses ``create_pydantic_model`` to serialize and deserialize data.

When using ``PiccoloCRUD``, you don't have to worry about serialisation because ``PiccoloCRUD`` 
internally uses ``create_pydantic_model`` to create a `Pydantic model <https://pydantic-docs.helpmanual.io/usage/models/>`_
from a Piccolo ``Table``. However, ``create_pydantic_model`` is very useful when
integrating Piccolo with a framework such as `FastAPI <https://github.com/tiangolo/fastapi>`_,
which also uses `Pydantic <https://github.com/samuelcolvin/pydantic>`_ for serialisation.

See the `create_pydantic_model docs <https://piccolo-orm.readthedocs.io/en/latest/piccolo/serialization/index.html>`_
for more details.