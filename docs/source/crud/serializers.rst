Serializers
===========

:class:`PiccoloCRUD<piccolo_api.crud.endpoints.PiccoloCRUD>` uses :func:`create_pydantic_model <piccolo.utils.pydantic.create_pydantic_model>`
internally to serialize and deserialize data.

:func:`create_pydantic_model <piccolo.utils.pydantic.create_pydantic_model>` is
very useful when integrating Piccolo with a framework such as `FastAPI <https://github.com/tiangolo/fastapi>`_,
which also uses `Pydantic <https://github.com/samuelcolvin/pydantic>`_ for
serialisation. It automatically creates Pydantic models for you.
