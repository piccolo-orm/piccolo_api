FastAPI
=======

`FastAPI <https://fastapi.tiangolo.com/>`_ is a powerful ASGI web framework,
built on top of `Starlette <https://www.starlette.io/>`_, which lets you build an API very easily, with
interactive docs.

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
        )
    )

We can now run this app using an ASGI server such as uvicorn.

.. code-block:: bash

    uvicorn app:app

Then try out the following:

 * OpenAPI docs: http://127.0.0.1:8000/docs/
 * API endpoint: http://127.0.0.1:8000/task/

To see a complete example of a FastAPI project built using Piccolo, see the
`piccolo_examples repo <https://github.com/piccolo-orm/piccolo_examples/tree/master/headless_blog_fastapi>`_.

Configuring the endpoints
-------------------------

If you want more control over the endpoints, you can do so using ``FastAPIKwargs``,
which allows you to specify additional arguments to pass into ``FastAPIApp.add_api_route``.

Example
~~~~~~~

In the following example, we add `tags <https://fastapi.tiangolo.com/tutorial/path-operation-configuration/#tags>`_
to the endpoints, which separates them in the docs UI.

We also mark one of the endpoints as deprecated.

.. code-block:: python

    from fastapi import FastAPI
    from piccolo_api.fastapi.endpoints import FastAPIWrapper, FastAPIKwargs
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
        fastapi_kwargs=FastAPIKwargs(
            all_routes={'tags': ['Task']},  # Added to all endpoints
            get={'deprecated': True},  # Just added to the 'get' endpoint
        )
    )

Source
------

.. currentmodule:: piccolo_api.fastapi.endpoints

.. autoclass:: FastAPIWrapper
