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


    asgi_app = Router([
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
    ])

    import uvicorn
    uvicorn.run(asgi_app)

jwt_login
---------

This creates an endpoint for logging in, and getting a JSON Web Token (JWT).

.. code-block:: python

    from starlette.routing import Route, Router
    from piccolo_api.endpoints.auth import jwt_login

    from .tables import User
    from settings import SECRET


    asgi_app = Router([
        Route(
            path="/login/",
            endpoint=jwt_login(
                auth_table=User,
                secret=SECRET
            )
        ),
    ])

    import uvicorn
    uvicorn.run(asgi_app)

Required arguments
~~~~~~~~~~~~~~~~~~

You have to pass in two arguments:

* auth_table - a subclass of Piccolo's ``BaseUser`` class, which is used to
  authenticate the user.
* secret - this is used for signing the JWT.

JWTMiddleware
-------------

blacklist
~~~~~~~~~

Optionally, you can pass in a ``blacklist`` argument, which is a subclass of
``JWTBlacklist``. The implementation of the ``in_blacklist`` method is up to
the user - the data could come from a database, a file, a Python list, or
anywhere else.

.. code-block:: python

    # An example blacklist.

    BLACKLISTED_TOKENS = ['abc123', 'def456']


    class MyBlacklist(JWTBlacklist):

        async def in_blacklist(self, token: str) -> bool:
            return token in BLACKLISTED_TOKENS


    jwt_login(
        auth_table=User,
        secret=SECRET,
        blacklist=MyBlacklist()
    )

.. hint:: Blacklists are important if you have tokens with a long expiry date.

.. todo - show example POST using requests
