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

In this example we're building the API for a task management app. Assuming
you have defined a Piccolo ``Table`` called ``Task``:

.. code-block:: python

    # app.py

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

We can now run this app using an ASGI server such as uvicorn.

.. code-block:: bash

    uvicorn app:app

Then try out the following:

 * OpenAPI docs: http://127.0.0.1:8000/docs/
 * API endpoint: http://127.0.0.1:8000/task/

To see a complete example of a FastAPI project built using Piccolo, see the
`piccolo_examples repo <https://github.com/piccolo-orm/piccolo_examples/tree/master/headless_blog_fastapi>`_.

Source
------

.. currentmodule:: piccolo_api.fastapi.endpoints

.. autoclass:: FastAPIWrapper
