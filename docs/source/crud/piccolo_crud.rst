PiccoloCRUD
===========

This creates an `ASGI <https://piccolo-orm.com/blog/introduction-to-asgi>`_ app,
which exposes the usual `CRUD <https://en.wikipedia.org/wiki/Create,_read,_update_and_delete>`_
methods on your Piccolo table, as well as some extras, via a `REST <https://en.wikipedia.org/wiki/Representational_state_transfer>`_
API.

-------------------------------------------------------------------------------

Endpoints
---------

========== ======================= ==========================================================================================================
Path       Methods                 Description
========== ======================= ==========================================================================================================
/          GET, POST, DELETE       Get all rows, post a new row, or delete all matching rows.
/<id>/     GET, PUT, DELETE, PATCH Get, update or delete a single row.
/schema/   GET                     Returns a JSON schema for the table. This allows clients to auto generate forms.
/ids/      GET                     Returns a mapping of all row ids to a description of the row.
/count/    GET                     Returns the number of matching rows.
/new/      GET                     Returns all of the default values for a new row - can be used to dynamically generate forms by the client.
========== ======================= ==========================================================================================================

-------------------------------------------------------------------------------

Creating an ASGI app
--------------------

Using it is as simple as this:

.. code-block:: python

    # app.py
    from piccolo_api.crud.endpoints import PiccoloCRUD

    from movies.tables import Movie


    # If we just want to expose the GET endpoints:
    app = PiccoloCRUD(table=Movie)

    # This will expose all the endpoints:
    app = PiccoloCRUD(table=Movie, read_only=False)

To expose several CRUD endpoints in our app, we use Starlette's Router.

.. code-block:: python

    # app.py
    from piccolo_api.crud.endpoints import PiccoloCRUD
    from starlette.routing import Mount, Router

    from movies.tables import Movie, Director


    app = Router([
        Mount(
            path='/movies',
            app=PiccoloCRUD(table=Movie),
        ),
        Mount(
            path='/directors',
            app=PiccoloCRUD(table=Director),
        ),
    ])

You can then run it using an ASGI server such as `Uvicorn <https://github.com/encode/uvicorn>`_:

.. code-block:: bash

    uvicorn app:app

-------------------------------------------------------------------------------

Filters
-------

Example schema
~~~~~~~~~~~~~~

``PiccoloCRUD`` makes filtering your data really easy using query parameters in
your HTTP request. Using the following Piccolo schema as an example:

.. code-block:: python

    # tables.py
    from piccolo.table import Table
    from piccolo.columns import (
        Varchar,
        Integer,
        ForeignKey,
        Boolean,
        Text,
        Timestamp,
        Numeric,
        Real
    )


    class Director(Table):
        name = Varchar(length=300, null=False)


    class Movie(Table):
        name = Varchar(length=300)
        rating = Real()
        duration = Integer()
        director = ForeignKey(references=Director)
        won_oscar = Boolean()
        description = Text()
        release_date = Timestamp()
        box_office = Numeric(digits=(5, 1))

Basic queries
~~~~~~~~~~~~~

Get all movies with 'star wars' in the name:

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?name=star%20wars

.. hint:: You can try these queries for yourself, but first login at https://demo1.piccolo-orm.com/
 using username: piccolo, password: piccolo123.

Operators
~~~~~~~~~

As shown above you can specify which operator to use. The allowed operator are:

 * lt: Less Than
 * lte: Less Equal Than
 * gt: Greater Than
 * gte: Greater Equal Than
 * e: Equal (default)

To specify which operator to use, pass a query parameter like ``field__operator=operator_name``.
For example ``duration__operator=gte``.

A query which fetches all movies lasting more than 200 minutes:

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?duration=200&duration__operator=gte

Match type
~~~~~~~~~~

When querying text fields (like ``Varchar`` and ``Text``), you can specify the
kind of match you're looking for.

 * contains
 * exact
 * starts
 * ends

To specify which match type to use, pass a query parameter like ``field__match=match_type``.
For example ``name__match=starts``.

A query which fetches all movies whose name begins with 'star wars':

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?name=star%20wars&name__match=starts

Sorting
~~~~~~~

To specify which field to sort by, pass a query parameter like ``__sorting=field``.
For example ``__sorting=name``.

A query which fetches all movies, sorted by duration:

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?__sorting=duration

You can reverse the sort by prepending '-' to the field. For example:

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?__sorting=-duration

-------------------------------------------------------------------------------

Source
------

.. currentmodule:: piccolo_api.crud.endpoints

.. autoclass:: PiccoloCRUD
