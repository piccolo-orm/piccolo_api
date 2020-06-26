FastAPI
=======

FastAPI is a powerful ASGI web framework, built on top of Starlette, which
lets you build an API very easily, with interactive docs.

It does this by making heavy use of type annotations.

By using ``FastAPIWrapper`` we can annotate our ``PiccoloCRUD`` endpoints so
FastAPI can automatically document them for us. It's an incredibly productive
way of building an API.

Example
-------

.. code-block:: python

    from fastapi import FastAPI
    from piccolo_api.fastapi.endpoints import FastAPIWrapper
    from piccolo_api.crud.endpoints import PiccoloCRUD

    from my_app.tables import Task


    app = FastAPI()


    FastAPIWrapper(
        root_url="/task/",
        fastapi_app=app,
        piccolo_crud=PiccoloCRUD(
            table=Task,
            read_only=False,
        ),
    )

Source
------

.. currentmodule:: piccolo_api.fastapi.endpoints

.. autoclass:: FastAPIWrapper
