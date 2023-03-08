Hooks
=====

Hooks allow executing custom code as part of processing a CRUD request. You can
use this to validate data, call another custom API, place messages on queues
and many other things.

-------------------------------------------------------------------------------

Enabling a hook
---------------

Define a method, and register it with :class:`PiccoloCRUD <piccolo_api.crud.endpoints.PiccoloCRUD>`:

.. code-block:: python

    # app.py
    from piccolo_api.crud.endpoints import PiccoloCRUD

    from movies.tables import Movie


    # set movie rating to 10 before saving
    async def set_movie_rating_10(row: Movie):
        row.rating = 10
        return row


    # set movie rating to 20 before saving
    async def set_movie_rating_10(row: Movie):
        row.rating = 20
        return row


    async def pre_delete(row_id):
        pass


    # Register one or multiple hooks
    app = PiccoloCRUD(
        table=Movie,
        read_only=False,
        hooks=[
            Hook(hook_type=HookType.pre_save, callable=set_movie_rating_10),
            Hook(hook_type=HookType.pre_save, callable=set_movie_rating_20),
            Hook(hook_type=HookType.pre_delete, callable=pre_delete)
        ]
    )

You can specify multiple hooks (also per ``hook_type``). Hooks are executed in order.
You can use either async or regular functions.

-------------------------------------------------------------------------------

Hook types
----------

There are different hook types, and each type takes a slightly different set of
inputs.

It's also important to return the expected data from your hook.

pre_save
~~~~~~~~

This hook runs during POST requests, prior to inserting data into the database.
It takes a single parameter, ``row``, and should return the row:

.. code-block:: python

    async def set_movie_rating_10(row: Movie):
        row.rating = 10
        return row


    app = PiccoloCRUD(table=Movie, read_only=False, hooks=[
        Hook(hook_type=HookType.pre_save, callable=set_movie_rating_10)
        ]
    )

pre_patch
~~~~~~~~~

This hook runs during PATCH requests, prior to changing the specified row in
the database.

It takes two parameters, ``row_id`` which is the id of the row to be changed,
and ``values`` which is a dictionary of incoming values.

Each function must return a dictionary which represent the data to be modified.

.. code-block:: python

    async def reset_name(row_id: int, values: dict):
        current_db_row = await Movie.objects().get(Movie.id==row_id)
        if values.get("name"):
            values["name"] = values["name"].replace(" ", "")
        return values


    app = PiccoloCRUD(
        table=Movie,
        read_only=False,
        hooks=[
            Hook(hook_type=HookType.pre_patch, callable=reset_name)
        ]
    )


pre_delete
~~~~~~~~~~

This hook runs during DELETE requests, prior to deleting the specified row in
the database.

It takes one parameter, ``row_id`` which is the id of the row to be deleted.

``pre_delete`` hooks should not return data.

.. code-block:: python

    async def pre_delete(row_id: int):
        pass


    app = PiccoloCRUD(
        table=Movie,
        read_only=False,
        hooks=[
            Hook(hook_type=HookType.pre_delete, callable=pre_delete)
        ]
    )

Dependency injection
~~~~~~~~~~~~~~~~~~~~

Each hook can optionally receive the ``Starlette`` request object. Just
add ``request`` as an argument in your hook, and it'll be injected automatically.

.. code-block:: python

    async def set_movie_rating_10(row: Movie, request: Request):
        ...

-------------------------------------------------------------------------------

Source
------

.. currentmodule:: piccolo_api.crud.hooks

HookType
~~~~~~~~

.. autoclass:: HookType
    :members:
    :undoc-members:

Hook
~~~~

.. autoclass:: Hook
