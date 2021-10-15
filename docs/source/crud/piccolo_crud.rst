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

As shown above you can specify which operator to use. The allowed operators are:

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

Order
~~~~~

To specify which field to sort by, pass a query parameter like ``__order=field``.
For example ``__order=name``.

A query which fetches all movies, sorted by duration:

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?__order=duration

You can reverse the sort by prepending '-' to the field. For example:

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?__order=-duration

Pagination
----------

LimitOffset Pagination
~~~~~~~~~~~~~~~~~~~~~~

You can specify how many results to return, and which page to return, using
the ``__page`` and ``__page_size`` query parameters.

For example, to return results 11 to 20:

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?__page=2&page_size=10

Cursor Pagination
~~~~~~~~~~~~~~~~~

For large data sets, you can use cursor pagination that has much better performance 
than LimitOffset pagination, but you need to be aware that cursor pagination has 
several trade offs. The cursor must be based on a unique and sequential column in the table. 
The client can't go to a specific page because there is no concept of the total number 
of pages or results.

Example usage of cursor:

.. code-block::

    GET http://localhost:8000/posts/?__page_size=3&__order=id&__cursor=NA== (ASC forward)
    GET http://localhost:8000/posts/?__page_size=3&__order=id&__cursor=NA==&__previous=yes (ASC backward)
    GET http://localhost:8000/posts/?__page_size=3&__order=-id&__cursor=OQ== (DESC forward)
    GET http://localhost:8000/posts/?__page_size=3&__order=-id&__cursor=OQ==&__previous=yes (DESC backward)

.. hint::
    Piccolo Api use id (primary key) column as unique column for cursor pagination.

.. warning::
    If you use ``__page`` and ``__cursor`` query parameters together in the same request, Piccolo Api 
    will raise ``HTTP 403 Forbbiden``.


Readable
--------

As foreign keys are just integers in Piccolo, they aren't very descriptive about
what is being pointed to. To get around this, each ``Table`` subclass can specify
a 'readable' representation, which is more descriptive, and readable for humans.
See the `Piccolo docs <https://piccolo-orm.readthedocs.io/en/latest/piccolo/schema/advanced.html#readable>`_
for more details.

If you'd like to retrieve the readable representations for each foreign key
in the queried table, you can do so by appending the `__readable=true`
parameter to your GET requests.

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/?__readable=true

Which returns something like this:

.. code-block:: javascript

    {
        "rows": [
            {
                "id": 17,
                "name": "The Hobbit: The Battle of the Five Armies",
                "rating": 59,
                "duration": 164,
                "director": 1,
                "director_readable": "Peter Jackson",  // <- Note
                "won_oscar": false,
                "description": "Bilbo fights against a number of enemies to save the life of his Dwarf friends and protects the Lonely Mountain after a conflict arises.",
                "release_date": "2014-12-01T00:00:00",
                "box_office": 956
            },
            ...
        ]
    }

You can also use this on GET requests when retrieving a single row, for example:

.. code-block::

    GET https://demo1.piccolo-orm.com/api/tables/movie/1/?__readable=true

-------------------------------------------------------------------------------

Source
------

.. currentmodule:: piccolo_api.crud.endpoints

.. autoclass:: PiccoloCRUD
