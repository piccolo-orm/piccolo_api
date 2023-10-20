Changes
=======

1.0.0
-----

Works with Piccolo v1, Piccolo Admin v1, and Pydantic v2.

-------------------------------------------------------------------------------

1.0a3
-----

Using the new ``json_schema_extra`` argument for ``create_pydantic_model``.

-------------------------------------------------------------------------------

1.0a2
-----

Fixed a bug with extracting the type from an optional type. Thanks to @sinisaos
for discovering this issue.

-------------------------------------------------------------------------------

1.0a1
-----

Pydantic v2 support - many thanks to @sinisaos for this.

-------------------------------------------------------------------------------

0.58.0
------

Upgraded the version of Swagger UI used in the ``swagger_ui`` endpoint (see
``piccolo_api.openapi.endpoints.swagger_ui``). Thanks to @sinisaos for this.

-------------------------------------------------------------------------------

0.57.0
------

``PiccoloCRUD`` now handles foreign key violation errors gracefully.

For example, if we have tables like this:

.. code-block:: python

  class Director(Table):
      name = Varchar()

  class Movie(Table):
      name = Varchar()
      director = ForeignKey(Director, on_delete=OnDelete.restrict)

The ``ON DELETE RESTRICT`` constraint means we're not allowed to delete a
director if a movie has a foreign key to it.

We now get a ``422`` error response, with an error message which we can display
in Piccolo Admin.

Support for Python 3.7 has also been dropped, as it's end of life.

-------------------------------------------------------------------------------

0.56.0
------

Version pinning Pydantic to v1, as v2 has breaking changes.

We will add support for Pydantic v2 in a future release.

Thanks to @sinisaos for helping with this.

-------------------------------------------------------------------------------

0.55.0
------

Added the ``excluded_paths`` argument to ``TokenAuthBackend``. This means you
can wrap an entire ASGI application in this middleware, and exclude certain
paths, such as the Swagger docs. Thanks to @sinisaos for this.

.. code-block:: python

    app = FastAPI(
        dependencies=[Depends(APIKeyHeader(name="Authorization"))],
        middleware=[
            Middleware(
                AuthenticationMiddleware,
                backend=TokenAuthBackend(
                    SecretTokenAuthProvider(tokens=["abc123"]),
                    excluded_paths=["/docs", "/openapi.json"],  # <- Note
                ),
            )
        ],
    )

-------------------------------------------------------------------------------

0.54.0
------

Added ``allow_unauthenticated`` option to ``JWTMiddleware``.

By default, ``JWTMiddleware`` rejects any request with an invalid JWT token,
but with this option we allow the user to reject the request instead within
their endpoints.

-------------------------------------------------------------------------------

0.53.0
------

Added ``token_login`` endpoint, which is more convenient than
``TokenAuthLoginEndpoint``.

Improved the docs for token auth and JWT auth (thanks to @sinisaos).

Modified the ``OrderBy`` class, to add some functionality needed by Piccolo
Admin.

-------------------------------------------------------------------------------

0.52.0
------

``PiccoloCRUD`` now lets you specify multiple columns in the ``__order`` GET
param.

For example, with this schema:

.. code-block:: python

  class Movie(Table):
      name = Varchar()
      rating = Integer()

To order the results by descending ``rating`` and ascending ``name``:

.. code-block::

  GET /?__order=-rating,name

-------------------------------------------------------------------------------

0.51.0
------

You can now get all rows with a null / not-null value in ``PiccoloCRUD``.

For example, if we have a nullable column called ``score``:

.. code-block::

  GET /?score__operator=is_null

Likewise, to get all rows whose score is not null:

.. code-block::

  GET /?score__operator=not_null

-------------------------------------------------------------------------------

0.50.0
------

Catching more database errors in ``PiccoloCRUD``, and returning useful API
responses instead of 500 errors.

Implemented GitHub's CodeQL suggestions - this now means ``LocalMediaStorage``
uses ``600`` instead of ``640`` as the default file permissions for uploaded
files (thanks to @sinisaos for this).

-------------------------------------------------------------------------------

0.49.0
------

* Added Python 3.11 support.
* ``PiccoloCRUD`` validators can now be async.
* Improved logging.
* The minimum version of FastAPI is now ``0.87.0``. The reason for this is
  Starlette made a fairly large change in version ``0.21.0``, which meant we
  had to refactor a lot of our tests, which makes it challenging to support
  older versions.

-------------------------------------------------------------------------------

0.48.1
------

Improving type annotations:

* Adding ``id: Serial`` for ``SessionsBase`` and ``TokenAuth``.
* Fixed type annotations for latest version of Starlette (thanks to @sinisaos
  for this).

-------------------------------------------------------------------------------

0.48.0
------

If ``BaseUser`` is used with ``PiccoloCRUD``, passwords are handled properly.
Thanks to @sinisaos for making this change.

-------------------------------------------------------------------------------

0.47.0
------

``PiccoloCRUD`` now handles database exceptions better. If a query fails due to
a unique constraint, a 422 response code is returned, along with information
about the error.

This means Piccolo Admin will show more useful debugging information when a
query fails.

Thanks to @ethagnawl for reporting this issue, and @sinisaos for help
prototyping a solution.

-------------------------------------------------------------------------------

0.46.0
------

Fixed a bug with ``Email`` columns and ``PiccoloCRUD.get_new``. Thanks to
@Tar8117 for reporting this bug.

-------------------------------------------------------------------------------

0.45.0
------

Previously you had to provide ``folder_name`` as an argument to
``S3MediaStorage``.

It's now optional, as some users may choose to store their files in a bucket
without a folder.

-------------------------------------------------------------------------------

0.44.0
------

When uploading files to S3, we try and correctly set the content type. This now
works correctly for ``.jpg`` files (previously only ``.jpeg`` worked for JPEGs
). Thanks to @sumitsharansatsangi for adding this.

-------------------------------------------------------------------------------

0.43.0
------

Fixed a bug with ``MediaStorage.delete_unused_files`` - it was raising an
exception when used with ``Array`` columns. Thanks to @sumitsharansatsangi for
reporting this issue.

When using ``S3MediaStorage`` you can now specify additional arguments when
files are uploaded (using the ``upload_metadata`` argument), for example,
setting the cache settings, and much more. Thanks to @sumitsharansatsangi, and
@sinisaos for help reviewing.

.. code-block:: python

  S3MediaStorage(
      ...,
      # Cache the file for 24 hours:
      upload_metadata={'CacheControl': 'max-age=86400'}
  )

-------------------------------------------------------------------------------

0.42.0
------

Added dependency injection to ``PiccoloCrud`` hooks - the Starlette request
object will now be passed in if requested. For example::

    def my_hook(row_id, request):
      ...

Thanks to @AnthonyArmour and @destos for this.

-------------------------------------------------------------------------------

0.41.0
------

Added support for file storage in a local folder and in S3. This was added for
Piccolo Admin, but is useful for all Piccolo apps. Thanks to @sinisaos for
assisting with this.

-------------------------------------------------------------------------------

0.40.0
------

Make Piccolo API work with Piccolo >= 0.82.0. ``Table`` used to accept a
parameter called ``ignore_missing``. This was renamed to ``_ignore_missing``.
Thanks to @sinisaos for this fix.

-------------------------------------------------------------------------------

0.39.0
------

Improved the HTTP status codes returned by the ``change_password``,
``register`` and ``session_login`` endpoints. They now return a 422 status
code if a validation error occurs. This is required by Piccolo Admin, to better
determine why a request failed.

-------------------------------------------------------------------------------

0.38.0
------

Added ``read_only`` option to ``change_password`` and ``register`` endpoints.

This is for Piccolo Admin's ``read_only`` mode.

-------------------------------------------------------------------------------

0.37.2
------

Changed a parameter name used in the ``change_password`` endpoint to be less
ambiguous (``old_password`` -> ``current_password``).

-------------------------------------------------------------------------------

0.37.1
------

Changed a parameter name used in the ``change_password`` endpoint to be less
ambiguous (``confirm_password`` -> ``confirm_new_password``).

-------------------------------------------------------------------------------

0.37.0
------

Added a ``change_password`` endpoint (courtesy @sinisaos).

See the `demo project <https://github.com/piccolo-orm/piccolo_api/tree/master/example_projects/change_password_demo>`_ for a full example.

-------------------------------------------------------------------------------

0.36.0
------

The ``session_login``, ``session_logout``, and ``register`` endpoints can now
have their CSS styles easily customised, to make them match the rest of the
application.

.. code-block:: python

    from fastapi import FastAPI
    from piccolo_api.session_auth.endpoints import register
    from piccolo_api.shared.auth.styles import Styles

    app = FastAPI()

    app.mount(
        '/register/',
        register(
            styles=Styles(background_color='black')
        )
    )

-------------------------------------------------------------------------------

0.35.0
------

It is now trivially easy to add CAPTCHA support to the ``register`` and
``session_login`` endpoints, to provide protection against bots. Just sign up
for an account with hCaptcha or reCAPTCHA, and do the following:

.. code-block:: python

    from fastapi import FastAPI
    from piccolo_api.session_auth.endpoints import register
    from piccolo_api.shared.auth.captcha import hcaptcha

    app = FastAPI()

    # To use hCaptcha:
    app.mount(
        '/register/',
        register(
            captcha=hcaptcha(
                site_key='my-site-key',
                secret_key='my-secret-key',
            )
        )
    )

-------------------------------------------------------------------------------

0.34.0
------

Added a ``register`` endpoint, which is great for quickly prototyping a sign up
process (courtesy @sinisaos).

Added hooks to the ``session_login`` endpoint, allowing additional logic to be
triggered before and after login.

-------------------------------------------------------------------------------

0.33.1
------

Fixing the ``ids`` endpoint of ``PiccoloCRUD`` when a custom primary key column
is used with a name other than ``id``.

-------------------------------------------------------------------------------

0.33.0
------

The schema endpoint of ``PiccoloCRUD`` now returns the primary key name. This
means we'll be able to support tables with a custom primary key name in Piccolo
Admin.

-------------------------------------------------------------------------------

0.32.3
------

Make sure tables with a custom primary key column work with ``PiccoloCRUD``.

-------------------------------------------------------------------------------

0.32.2
------

Fixed a bug with ``PiccoloCRUD``, where a PATCH request returned a string
instead of a JSON object. Thanks to @trondhindenes for discovering and fixing
this issue.

-------------------------------------------------------------------------------

0.32.1
------

Fixed bug with ``__range_header=false``.

-------------------------------------------------------------------------------

0.32.0
------

Added support for the ``Content-Range`` HTTP header in the GET endpoint of
``PiccoloCRUD``. This means the API client can fetch the number of available
rows, without doing a separate API call to the ``count`` endpoint.

.. code-block::

  GET /?__range_header=true

If the page size is 10, then the response header then looks something like:

.. code-block::

  Content-Range: movie 0-9/100

The feature was created to make Piccolo APIs work better with front ends like
`React Admin <https://marmelab.com/react-admin/>`_.

Thanks to @trondhindenes for adding this feature, and @sinisaos for help
reviewing.

-------------------------------------------------------------------------------

0.31.0
------

Added hooks to ``PiccoloCRUD``. This allows the user to add their own logic
before a save / patch / delete (courtesy @trondhindenes).

For example:

.. code-block:: python

  # Normal functions and async functions are supported:
  def pre_save_hook(movie):
      movie.rating = 90
      return movie

  PiccoloCRUD(
      table=Movie,
      read_only=False,
      hooks=[
          Hook(hook_type=HookType.pre_save, callable=pre_save_hook)
      ]
  )

-------------------------------------------------------------------------------

0.30.1
------

* Streamlined the ``CSRFMiddleware`` code, and added missing type annotations.
* If using the ``__visible_fields`` parameter with ``PiccoloCRUD``, and the
  field name is unrecognised, the error response will list the correct field
  names.
* Improved test coverage (courtesy @sinisaos).

-------------------------------------------------------------------------------

0.30.0
------

We recently added the ``__visible_fields`` GET parameter to  ``PiccoloCRUD``,
which allows the user to determine which fields are returned by the API.

However, there was no way of the user knowing which fields were supported. This
is now possible by visiting the ``/schema`` endpoint, which has a
``visible_fields_options`` field which lists the columns available on the table
and related tables (courtesy @sinisaos).

-------------------------------------------------------------------------------

0.29.2
------

Fixed a bug with the OpenAPI docs when using ``Array`` columns. Thanks to @gmos
for reporting this issue, and @sinisaos for fixing it.

-------------------------------------------------------------------------------

0.29.1
------

The ``__visible_fields`` filter on ``PiccoloCRUD`` now works on the detail
endpoint (courtesy @sinisaos). For example:

.. code-block:: text

  GET /1/?__visible_fields=id,name,director.name

We also modified a type annotation in ``FastAPIWrapper``, so  you can use it
with FastAPI's ``APIRouter`` without getting a type warning. Thanks to @gmos
for reporting this issue.

-------------------------------------------------------------------------------

0.29.0
------

Added a ``__visible_fields`` filter to ``PiccoloCRUD``. It's a very powerful
feature which lets us specify which fields we want the API to return from a
GET request (courtesy @sinisaos).

It can even support joins, but we must supply a ``max_joins`` parameter:

.. code-block:: python

    app = PiccoloCRUD(Movie, max_joins=1)
    uvicorn(app)

Then we can do:

.. code-block:: text

  GET /?__visible_fields=id,name,director.name

Which will return:

.. code-block:: javascript

  {
    "rows": [
        {
            "id": 17,
            "name": "The Hobbit: The Battle of the Five Armies",
            "director": {
                "name": "Peter Jackson"
            }
        },
        ...
    ]
  }

By specifying exactly which data we want returned, it is much more efficient,
especially when fetching large numbers of rows, or with tables with lots of
columns.

-------------------------------------------------------------------------------

0.28.1
------

Fixed a bug with the delete endpoint of ``PiccoloCRUD``. It was returning a 204
response with a body (this isn't allowed, and could cause an exception to be
raised in the web server). Thanks to @trondhindenes for reporting this issue.

Updated Swagger UI to the latest version.

-------------------------------------------------------------------------------

0.28.0
------

Modified the ``get_ids`` endpoint of ``PiccoloCRUD``, so it accepts an
``offset`` query parameter. It already supported ``limit``.

-------------------------------------------------------------------------------

0.27.0
------

You can now pass a ``schema_extra`` argument to ``PiccoloCRUD``, which is
added to the underlying Pydantic schema.

-------------------------------------------------------------------------------

0.26.0
------

``create_pydantic_model`` is now imported from the main Piccolo repo.

-------------------------------------------------------------------------------

0.25.1
------

* Added examples to CSRF docs (courtesy @sinisaos).
* Improved ``SessionAuthBackend`` - it was too aggressive at rejecting
  requests when ``allow_unauthenticated=True`` (thanks to @Bakz for reporting
  this).

-------------------------------------------------------------------------------

0.25.0
------

If you send a GET request to the ``session_logout`` endpoint, it will now
render a simple logout form. This makes it work much nicer out of the box.
Thanks to @sinisaos for adding this.

-------------------------------------------------------------------------------

0.24.1
------

When using the ``nested` argument in ``create_pydantic_model``, more of the
other arguments are passed to the nested models. For example, if
``include_default_columns`` is ``True``, both the parent and child models will
include their default columns.

-------------------------------------------------------------------------------

0.24.0
------

Added support for nested models in ``create_pydantic_model``. For each
``ForeignKey`` in the Piccolo table, the Pydantic model will contain a sub
model for the related table.

For example:

.. code-block::

  class Manager(Table):
      name = Varchar()

  class Band(Table):
      name = Varchar()
      manager = ForeignKey(Manager)

  BandModel = create_pydantic_model(Band, nested=True)

If we were to write ``BandModel`` by hand instead, it would look like this:

.. code-block::

  class ManagerModel(BaseModel):
      name: str

  class BandModel(BaseModel):
      name: str
      manager: ManagerModel

This feature is designed to work with the new ``nested`` output option in
Piccolo >= 0.40.0, which returns the data in the correct format to pass
directly to the nested Pydantic model.

.. code-block::

  band = Band.select(
      Band.id,
      Band.name,
      *Band.manager.all_columns()
  ).first(
  ).output(
      nested=True
  ).run_sync()
  >>> print(band)
  {'id': 1, 'name': 'Pythonistas', 'manager': {'id': 1, 'name': 'Guido'}}

  BandModel(**band)

Courtesy @aminalaee.

-------------------------------------------------------------------------------

0.23.1
------

Make sure ``asyncpg`` gets installed, as Piccolo API currently has a hard
requirement on it (we hope to fix this in the future).

-------------------------------------------------------------------------------

0.23.0
------

* Fixed MyPy errors (courtesy @sinisaos).
* Simplification of JWT authentication - it no longer needlessly checks
  expiry, as PyJWT already does this (courtesy @aminalaee).
* Substantial increase in code coverage (courtesy @aminalaee and @sinisaos).
* Increased the minimum PyJWT version, as versions > 2.0.0 return the JWT as a
  string instead of bytes.
* Added an option to exclude columns when using ``create_pydantic_model``
  (courtesy @kucera-lukas).

-------------------------------------------------------------------------------

0.22.0
------

Updating ``PiccoloCRUD`` so it works better with the custom primary key feature
added in Piccolo.

-------------------------------------------------------------------------------

0.21.1
------

Minor changes to the custom login template logic. More complex Jinja templates
are now supported (which are extended from other Jinja templates).

-------------------------------------------------------------------------------

0.21.0
------

Session auth improvements:

* The default login template is much nicer now.
* The login template can be overridden with a custom one, to match the look
  and feel of the application.
* The ``session_logout`` endpoint can now redirect after successfully logging
  out.

-------------------------------------------------------------------------------

0.20.0
------

When using the ``swagger_ui`` endpoint, the title can now be customised -
courtesy @heliumbrain.

-------------------------------------------------------------------------------

0.19.0
------

* Added an ``allow_unauthenticated`` option to ``SessionsAuthBackend``, which
  will add an ``UnauthenticatedUser`` to the scope, instead of rejecting the
  request. The app's endpoints are then responsible for checking
  ``request.user.is_authenticated``.
* Improved the docs for Session Auth.
* If ``deserialize_json`` is False on ``create_pydantic_model``, it will
  still provide some JSON validation.

-------------------------------------------------------------------------------

0.18.0
------
Added a ``deserialize_json`` option to ``create_pydantic_model``, which will
convert JSON strings to objects - courtesy @heliumbrain.

-------------------------------------------------------------------------------

0.17.1
------

Added the OAuth redirect endpoint to ``swagger_ui``.

-------------------------------------------------------------------------------

0.17.0
------

Added a ``swagger_ui`` endpoint which works with Piccolo's ``CSRFMiddleware``.

-------------------------------------------------------------------------------

0.16.0
------

Modified the auth middleware to add the Piccolo ``BaseUser`` instance for the
authenticated user to Starlette's ``BaseUser``.

-------------------------------------------------------------------------------

0.15.1
------

Add missing `login.html` template.

-------------------------------------------------------------------------------

0.15.0
------

Added support for ``choices`` argument in Piccolo ``Column`` instances. The
choices are output in the schema endpoint of ``PiccoloCRUD``.

-------------------------------------------------------------------------------

0.14.1
------

Added ``validators`` and ``exclude_secrets`` arguments to ``PiccoloCRUD``.

-------------------------------------------------------------------------------

0.14.0
------

Added ``superuser_only`` and ``active_only`` options to ``SessionsAuthBackend``.

-------------------------------------------------------------------------------

0.13.0
------

Added support for ``Array`` column types.

-------------------------------------------------------------------------------

0.12.13
-------

Added ``py.typed`` file, for MyPy.

-------------------------------------------------------------------------------

0.12.12
-------

Exposing the ``help_text`` value for ``Table`` in the Pydantic schema.

-------------------------------------------------------------------------------

0.12.11
-------

Exposing the ``help_text`` value for ``Column`` in the Pydantic schema.

-------------------------------------------------------------------------------

0.12.10
-------

Fixing a bug with ``ids`` endpoint when there's a limit but no search.

-------------------------------------------------------------------------------

0.12.9
------

Fixing ``ids`` endpoint in ``PiccoloCRUD`` with Postgres - search wasn't
working.

-------------------------------------------------------------------------------

0.12.8
------

The ``ids`` endpoint in ``PiccoloCRUD`` now accepts a limit parameter.

-------------------------------------------------------------------------------

0.12.7
------

Added additional validation to Pydantic serialisers - for example, ``Varchar``
max length, and ``Decimal`` / ``Numeric`` precision and scale.

-------------------------------------------------------------------------------

0.12.6
------

The ``ids`` endpoint in ``PiccoloCRUD`` is now searchable.

-------------------------------------------------------------------------------

0.12.5
------

Added missing ``new`` endpoint to ``FastAPIWrapper`` - courtesy @sinisaos.

-------------------------------------------------------------------------------

0.12.4
------

Made FastAPI a requirements, instead of an optional requirement.

-------------------------------------------------------------------------------

0.12.3
------

* Added ids and references endpoints to ``FastAPIWrapper``.
* Increase compatibility of ``SessionLoginEndpoint`` and ``CSRFMiddleware`` -
  adding a CSRF token as a form field should now work.

-------------------------------------------------------------------------------

0.12.2
------

* Added docstrings to FastAPI endpoints in ``FastAPIWrapper``.
* Exposing count and schema endpoints in ``FastAPIWrapper``.

-------------------------------------------------------------------------------

0.12.1
------

* Added docs for ``__page`` and ``__page_size`` query parameters for
  ``PiccoloCRUD``.
* Implemented ``max_page_size`` to prevent excessive server load  - courtesy
  @sinisaos.

-------------------------------------------------------------------------------

0.12.0
------

Renaming migrations which were problematic for Windows users.

-------------------------------------------------------------------------------

0.11.4
------

Using Pydantic to serialise the ``PiccoloCRUD.new`` response. Fixes a bug
with serialising some values, such as ``decimal.Decimal``.

-------------------------------------------------------------------------------

0.11.3
------

* Using Piccolo's ``run_sync`` instead of asgiref.
* Loosened dependencies.
* ``create_pydantic_model`` now supports lazy references in ``ForeignKey``
  columns.
* MyPy fixes.

-------------------------------------------------------------------------------

0.11.2
------

* ``PiccoloCRUD`` now supports the `__readable` query parameter for detail
  endpoints - i.e. `/api/movie/1/?__readable=true`. Thanks to sinisaos for
  the initial prototype.
* Improving type hints.

-------------------------------------------------------------------------------

0.11.1
------

Bumped requirements.

-------------------------------------------------------------------------------

0.11.0
------

Using ``Column._meta.required`` for Pydantic schema.

-------------------------------------------------------------------------------

0.10.1
------

Can pass more configuration options to FastAPI via ``FastAPIWrapper``.

-------------------------------------------------------------------------------

0.10.0
------

Updated for Piccolo 0.12.

-------------------------------------------------------------------------------

0.9.2
-----

* Added ``FastAPIWrapper``, which makes building a FastAPI endpoint really
  simple.
* Improved the handling of malformed queries better in ``PiccoloCRUD`` -
  catching unrecognised column names, and returning a 400 response.

-------------------------------------------------------------------------------

0.9.1
-----

``create_pydantic_model`` now accepts an optional `model_name` argument.

-------------------------------------------------------------------------------

0.9.0
-----

Bumped requirements, to support Piccolo ``Numeric`` and ``Real`` column types.

-------------------------------------------------------------------------------

0.8.0
-----

Improved session auth - can increase the expiry automatically, which improves
the user experience.

-------------------------------------------------------------------------------

0.7.6
-----

Can choose to not redirect after a successful session auth login - this is
preferred when calling the endpoint via AJAX.

-------------------------------------------------------------------------------

0.7.5
-----

Loosening requirements for Piccolo projects.

-------------------------------------------------------------------------------

0.7.4
-----

Bumped requirements.

-------------------------------------------------------------------------------

0.7.3
-----

Bumped requirements.

-------------------------------------------------------------------------------

0.7.2
-----

Can configure where ``CSRFMiddleware`` looks for tokens, and bug fixes.

-------------------------------------------------------------------------------

0.7.1
-----

CSRF tokens can now be passed as form values.

-------------------------------------------------------------------------------

0.7.0
-----

Supporting Piccolo 0.10.0.

-------------------------------------------------------------------------------

0.6.1
-----

Adding missing __init__.py file - was messing up release.

-------------------------------------------------------------------------------

0.6.0
-----

New style migrations.

-------------------------------------------------------------------------------

0.5.1
-----

Added support for PATCH queries, and specifying text filter types, to
``PiccoloCRUD``.

-------------------------------------------------------------------------------

0.5.0
-----

Changed schema format.

-------------------------------------------------------------------------------

0.4.4
-----

``PiccoloCRUD`` 'new' endpoint works in readonly mode - doesn't save any data.

-------------------------------------------------------------------------------

0.4.3
-----

Supporting order by, pagination, and filter operators in ``PiccoloCRUD``.

-------------------------------------------------------------------------------

0.4.2
-----

Added 'new' endpoint to ``PiccoloCRUD``.

-------------------------------------------------------------------------------

0.4.1
-----

Added missing ``__init__.py`` files.

-------------------------------------------------------------------------------

0.4.0
-----

Added token auth and rate limiting middleware.

-------------------------------------------------------------------------------

0.3.2
-----

Updated Piccolo import paths.

-------------------------------------------------------------------------------

0.3.1
-----

Updated Piccolo syntax.

-------------------------------------------------------------------------------

0.3.0
-----

Improved code layout.

-------------------------------------------------------------------------------

0.2.0
-----

Updating to work with Piccolo > 0.5.

-------------------------------------------------------------------------------

0.1.3
-----

Added validation to PUT requests.

-------------------------------------------------------------------------------

0.1.2
-----

Added foreign key support to schema.

-------------------------------------------------------------------------------

0.1.1
-----

Changed import paths.
