What's Piccolo API?
===================

Piccolo API makes it easy to turn your `Piccolo ORM <https://piccolo-orm.readthedocs.io/en/latest/>`_
tables into a working REST API.

PiccoloCRUD
-----------

This creates an `ASGI <https://piccolo-orm.com/blog/introduction-to-asgi>`_ app,
which exposes the usual CRUD methods on your table, as well as some extras.

========== ===================
Path       Methods
========== ===================
/          GET, POST, DELETE
/<id>/     GET, PUT, DELETE
/schema/   GET
/ids/      GET
========== ===================

Example
~~~~~~~

Using it is as simple as this:

.. code-block:: python

    from piccolo_api.endpoints.crud import PiccoloCRUD

    from .tables import MyTable


    # If we just want to expose the GET endpoints:
    asgi_app = PiccoloCRUD(table=MyTable)

    # This will expose all the endpoints:
    asgi_app = PiccoloCRUD(table=MyTable, read_only=False)

    # You can mount this to an existing ASGI app, or just run it directly:
    import uvicorn
    uvicorn.run(asgi_app)

To expose several CRUD endpoints in our app, we use Starlette's Router.

.. code-block:: python

    from piccolo_api.endpoints.crud import PiccoloCRUD
    from starlette.routing import Mount, Router

    from .tables import Table1, Table2, Table3


    asgi_app = Router(
        Mount(
            path='/table1',
            app=PiccoloCRUD(table=Table1),
        ),
        Mount(
            path='/table2',
            app=PiccoloCRUD(table=Table2),
        ),
        Mount(
            path='/table3',
            app=PiccoloCRUD(table=Table3),
        ),
    )

    import uvicorn
    uvicorn.run(asgi_app)

jwt_login
---------

...
