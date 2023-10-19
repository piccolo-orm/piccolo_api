from enum import Enum
from unittest import TestCase

from piccolo.apps.user.tables import BaseUser
from piccolo.columns import Email, ForeignKey, Integer, Secret, Text, Varchar
from piccolo.columns.column_types import OnDelete
from piccolo.columns.readable import Readable
from piccolo.table import Table, create_db_tables_sync, drop_db_tables_sync
from starlette.datastructures import QueryParams
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import (
    GreaterThan,
    OrderBy,
    ParamException,
    PiccoloCRUD,
    get_visible_fields_options,
)


class Movie(Table):
    name = Varchar(length=100, required=True)
    rating = Integer()

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])


class Role(Table):
    movie = ForeignKey(Movie)
    name = Varchar(length=100)


class TopSecret(Table):
    name = Varchar()
    confidential = Secret()


class Studio(Table):
    name = Varchar()
    contact_email = Email()
    booking_email = Email(default="booking@studio.com")


class Cinema(Table):
    name = Varchar()
    address = Text(unique=True)


class Ticket(Table):
    code = Varchar(null=False)


class TestGetVisibleFieldsOptions(TestCase):
    def test_without_joins(self):
        response = get_visible_fields_options(table=Role, max_joins=0)
        self.assertEqual(response, ("id", "movie", "name"))

    def test_with_joins(self):
        response = get_visible_fields_options(table=Role, max_joins=1)
        self.assertEqual(
            response,
            ("id", "movie", "movie.id", "movie.name", "movie.rating", "name"),
        )


class TestSplitParams(TestCase):
    """
    Make sure the HTTP parameters are parsed correctly.
    """

    def setUp(self):
        self.crud = PiccoloCRUD(Movie)

    def test_page(self):
        self.assertEqual(self.crud._split_params({"__page": 2}).page, 2)

        with self.assertRaises(ParamException):
            self.crud._split_params({"__page": "one"})

    def test_page_size(self):
        self.assertEqual(
            self.crud._split_params({"__page_size": 5}).page_size, 5
        )

        with self.assertRaises(ParamException):
            self.crud._split_params({"__page_size": "one"})

    def test_order(self):
        self.assertListEqual(
            self.crud._split_params({"__order": "id"}).order_by,
            [OrderBy(Movie.id, ascending=True)],
        )

        self.assertListEqual(
            self.crud._split_params({"__order": "id,name"}).order_by,
            [
                OrderBy(Movie.id, ascending=True),
                OrderBy(Movie.name, ascending=True),
            ],
        )

        self.assertListEqual(
            self.crud._split_params({"__order": "id,-name"}).order_by,
            [
                OrderBy(Movie.id, ascending=True),
                OrderBy(Movie.name, ascending=False),
            ],
        )

        self.assertIsNone(self.crud._split_params({}).order_by)

    def test_readable(self):
        for value in ("t", "true", "True", "1"):
            self.assertEqual(
                self.crud._split_params(
                    {"__readable": value}
                ).include_readable,
                True,
                msg=f"Testing {value}",
            )

        with self.assertRaises(ParamException):
            self.crud._split_params({"__readable": "ok"})

    def test_operator(self):
        split_params = self.crud._split_params(
            {"age__operator": "gt", "rating": 25}
        )
        self.assertEqual(split_params.operators["age"], GreaterThan)
        self.assertEqual(
            split_params.fields,
            {"rating": 25},
        )

    def test_visible_fields(self):
        self.assertEqual(
            self.crud._split_params(
                {"__visible_fields": "id,name"}
            ).visible_fields,
            [Movie.id, Movie.name],
        )

        with self.assertRaises(ParamException):
            self.crud._split_params({"__visible_fields": "foobar"})


class TestPatch(TestCase):
    def setUp(self):
        BaseUser.create_table(if_not_exists=True).run_sync()
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        BaseUser.alter().drop_table().run_sync()
        Movie.alter().drop_table().run_sync()

    def test_patch_succeeds(self):
        """
        Make sure a patch modifies the underlying database, and returns the
        new row data.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        rating = 93
        movie = Movie(name="Star Wars", rating=rating)
        movie.save().run_sync()

        new_name = "Star Wars: A New Hope"

        response = client.patch(f"/{movie.id}/", json={"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)

        # Make sure the row is returned:
        response_json = response.json()
        self.assertEqual(response_json["name"], new_name)
        self.assertEqual(response_json["rating"], rating)

        # Make sure the underlying database row was changed:
        movies = Movie.select().run_sync()
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0]["name"], new_name)

    def test_patch_user_new_password(self):
        client = TestClient(PiccoloCRUD(table=BaseUser, read_only=False))

        json = {
            "username": "John",
            "password": "John123",
            "email": "john@test.com",
            "active": False,
            "admin": False,
            "superuser": False,
        }

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 201)

        user = BaseUser.select().first().run_sync()

        json = {
            "email": "john@test.com",
            "password": "123456",
            "active": True,
            "admin": False,
            "superuser": False,
        }

        response = client.patch(f"/{user['id']}/", json=json)
        self.assertEqual(response.status_code, 200)

    def test_patch_user_old_password(self):
        client = TestClient(PiccoloCRUD(table=BaseUser, read_only=False))

        json = {
            "username": "John",
            "password": "John123",
            "email": "john@test.com",
            "active": False,
            "admin": False,
            "superuser": False,
        }

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 201)

        user = BaseUser.select().first().run_sync()

        json = {
            "email": "john@test.com",
            "password": "",
            "active": True,
            "admin": False,
            "superuser": False,
        }

        response = client.patch(f"/{user['id']}/", json=json)
        self.assertEqual(response.status_code, 200)

    def test_patch_user_fails(self):
        client = TestClient(PiccoloCRUD(table=BaseUser, read_only=False))

        json = {
            "username": "John",
            "password": "John123",
            "email": "john@test.com",
            "active": False,
            "admin": False,
            "superuser": False,
        }

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 201)

        user = BaseUser.select().first().run_sync()

        json = {
            "email": "john@test.com",
            "password": "1",
            "active": True,
            "admin": True,
            "superuser": False,
        }

        with self.assertRaises(ValueError):
            response = client.patch(f"/{user['id']}/", json=json)
            self.assertEqual(response.content, b"The password is too short.")

    def test_patch_fails(self):
        """
        Make sure a patch containing the wrong columns is rejected.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.patch(f"/{movie.id}/", json={"foo": "bar"})
        self.assertEqual(response.status_code, 400)

    def test_patch_validation_error(self):
        """
        Check if Pydantic validation error works.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.patch(
            f"/{movie.id}/",
            json={"name": 95, "rating": "95"},
        )
        self.assertIn("validation error", str(response.content))
        self.assertEqual(response.status_code, 400)

        # Make sure nothing changed in the database:
        self.assertListEqual(
            Movie.select(Movie.name, Movie.rating).run_sync(),
            [{"name": "Star Wars", "rating": 93}],
        )


class TestIDs(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_get_ids(self):
        """
        Make sure get_ids returns a mapping of an id to a readable
        representation of the row.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.get("/ids/")
        self.assertEqual(response.status_code, 200)

        # Make sure the content is correct:
        response_json = response.json()
        self.assertEqual(response_json[str(movie.id)], "Star Wars")

    def test_get_ids_with_search(self):
        """
        Test the search parameter.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=90),
        ).run_sync()

        for search_term in ("star", "Star", "Star Wars", "STAR WARS"):
            response = client.get(f"/ids/?search={search_term}")
            self.assertEqual(response.status_code, 200)

            # Make sure the content is correct:
            response_json = response.json()
            self.assertEqual(len(response_json), 1)
            self.assertIn("Star Wars", response_json.values())

    def test_get_ids_with_limit_offset(self):
        """
        Test the limit and offset parameter.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=90),
        ).run_sync()

        response = client.get("/ids/?limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"1": "Star Wars"})

        # Make sure only valid limit values are accepted.
        response = client.get("/ids/?limit=abc")
        self.assertEqual(response.status_code, 400)

        # Make sure only valid offset values are accepted.
        response = client.get("/ids/?offset=abc")
        self.assertEqual(response.status_code, 400)

        # Test with offset
        response = client.get("/ids/?limit=1&offset=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"2": "Lord of the Rings"})


class TestCount(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_get_count(self):
        """
        Make sure the correct count is returned.
        """
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, page_size=15)
        )

        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=93),
        ).run_sync()

        response = client.get("/count/")
        self.assertEqual(response.status_code, 200)

        # Make sure the count is correct:
        response_json = response.json()
        self.assertEqual(response_json, {"count": 2, "page_size": 15})

        # Make sure filtering works with count queries.
        response = client.get("/count/?name=Star%20Wars")
        response_json = response.json()
        self.assertEqual(response_json, {"count": 1, "page_size": 15})


class TestReferences(TestCase):
    def setUp(self):
        for table in (Movie, Role):
            table.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        for table in (Role, Movie):
            table.alter().drop_table().run_sync()

    def test_get_references(self):
        """
        Make sure the table's references are returned.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        role = Role(name="Luke Skywalker", movie=movie.id)
        role.save().run_sync()

        response = client.get("/references/")
        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertEqual(
            response_json,
            {"references": [{"tableName": "role", "columnName": "movie"}]},
        )


class TestSchema(TestCase):
    def setUp(self):
        for table in (Movie, Role):
            table.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        for table in (Role, Movie):
            table.alter().drop_table().run_sync()

    def test_get_schema(self):
        """
        Make sure the schema is returned correctly.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        response = client.get("/schema/")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json(),
            {
                "extra": {
                    "help_text": None,
                    "primary_key_name": "id",
                    "visible_fields_options": ["id", "name", "rating"],
                },
                "properties": {
                    "name": {
                        "extra": {
                            "choices": None,
                            "help_text": None,
                            "nullable": False,
                            "secret": False,
                        },
                        "maxLength": 100,
                        "title": "Name",
                        "type": "string",
                    },
                    "rating": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}],
                        "default": None,
                        "extra": {
                            "choices": None,
                            "help_text": None,
                            "nullable": False,
                            "secret": False,
                        },
                        "title": "Rating",
                    },
                },
                "required": ["name"],
                "title": "MovieIn",
                "type": "object",
            },
        )

    def test_get_schema_with_choices(self):
        """
        Make sure that if a Table has columns with choices specified, they
        appear in the schema.
        """

        class Review(Table):
            class Rating(Enum):
                bad = 1
                average = 2
                good = 3
                great = 4

            score = Integer(choices=Rating)

        client = TestClient(PiccoloCRUD(table=Review, read_only=False))

        response = client.get("/schema/")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json(),
            {
                "extra": {
                    "help_text": None,
                    "primary_key_name": "id",
                    "visible_fields_options": ["id", "score"],
                },
                "properties": {
                    "score": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}],
                        "default": None,
                        "extra": {
                            "choices": {
                                "average": {
                                    "display_name": "Average",
                                    "value": 2,
                                },
                                "bad": {"display_name": "Bad", "value": 1},
                                "good": {"display_name": "Good", "value": 3},
                                "great": {"display_name": "Great", "value": 4},
                            },
                            "help_text": None,
                            "nullable": False,
                            "secret": False,
                        },
                        "title": "Score",
                    }
                },
                "title": "ReviewIn",
                "type": "object",
            },
        )

    def test_get_schema_with_joins(self):
        """
        Make sure that if a Table has columns with joins specified, they
        appear in the schema.
        """
        client = TestClient(
            PiccoloCRUD(table=Role, read_only=False, max_joins=1)
        )

        response = client.get("/schema/")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json(),
            {
                "extra": {
                    "help_text": None,
                    "primary_key_name": "id",
                    "visible_fields_options": [
                        "id",
                        "movie",
                        "movie.id",
                        "movie.name",
                        "movie.rating",
                        "name",
                    ],
                },
                "properties": {
                    "movie": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}],
                        "default": None,
                        "extra": {
                            "choices": None,
                            "foreign_key": {
                                "target_column": "id",
                                "to": "movie",
                            },
                            "help_text": None,
                            "nullable": True,
                            "secret": False,
                        },
                        "title": "Movie",
                    },
                    "name": {
                        "anyOf": [
                            {"maxLength": 100, "type": "string"},
                            {"type": "null"},
                        ],
                        "default": None,
                        "extra": {
                            "choices": None,
                            "help_text": None,
                            "nullable": False,
                            "secret": False,
                        },
                        "title": "Name",
                    },
                },
                "title": "RoleIn",
                "type": "object",
            },
        )


class TestDeleteSingle(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_delete_single(self):
        """
        Make sure an existing row is deleted successfully.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.delete(f"/{movie.id}/")
        self.assertEqual(response.status_code, 204)

        self.assertEqual(Movie.count().run_sync(), 0)

    def test_delete_404(self):
        """
        Should get a 404 if a matching row doesn't exist.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        response = client.delete("/123/")
        self.assertEqual(response.status_code, 404)


class TestPut(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_put_existing(self):
        """
        Should get a 204 if an existing row has been updated.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.put(
            f"/{movie.id}/",
            json={"name": "Star Wars: A New Hope", "rating": 95},
        )
        self.assertEqual(response.status_code, 204)

        self.assertEqual(Movie.count().run_sync(), 1)

    def test_put_validation_error(self):
        """
        Check if Pydantic validation error works.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.put(
            f"/{movie.id}/",
            json={"name": 95, "rating": "95"},
        )
        self.assertIn("validation error", str(response.content))
        self.assertEqual(response.status_code, 400)

        self.assertEqual(Movie.count().run_sync(), 1)

    def test_put_new(self):
        """
        We expect a 404 - we don't allow PUT requests to create new resources.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        response = client.put("/123/")
        self.assertEqual(response.status_code, 404)


class TestGetAll(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        Movie(name="Lord of the Rings", rating=90).save().run_sync()

        Role.create_table(if_not_exists=True).run_sync()
        Role(name="Luke Skywalker", movie=movie.id).save().run_sync()

    def tearDown(self):
        for table in (Role, Movie):
            table.alter().drop_table().run_sync()

    def test_basic(self):
        """
        Make sure that bulk GETs return the correct data.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        rows = Movie.select().order_by(Movie.id).run_sync()

        response = client.get("/", params={"__order": "id"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": rows})

    def test_order(self):
        """
        Make sure multiple __order arguments can be passed in.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        # Insert another row with a matching rating.
        Movie(name="Blade Runner", rating=90).save().run_sync()

        rows = (
            Movie.select()
            .order_by(Movie.rating)
            .order_by(Movie.name)
            .run_sync()
        )

        # Multiple params should work.
        response = client.get(
            "/", params=(("__order", "rating"), ("__order", "name"))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": rows})

        # As should a single comma separated string.
        response = client.get("/", params={"__order": "rating,name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": rows})

        # Try with descending order.
        rows = (
            Movie.select()
            .order_by(Movie.rating, ascending=False)
            .order_by(Movie.name)
            .run_sync()
        )
        response = client.get("/", params={"__order": "-rating,name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": rows})

    ###########################################################################

    def test_visible_fields(self):
        """
        Make sure that GETs with the ``__visible_fields`` parameter return the
        correct data.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        # Test a simple query
        response = client.get(
            "/", params={"__visible_fields": "id,name", "__order": "id"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {"id": 1, "name": "Star Wars"},
                    {"id": 2, "name": "Lord of the Rings"},
                ]
            },
        )

        # Test using multiple params
        response = client.get(
            "/",
            params=(
                ("__visible_fields", "id"),
                ("__visible_fields", "name"),
                ("__order", "id"),
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {"id": 1, "name": "Star Wars"},
                    {"id": 2, "name": "Lord of the Rings"},
                ]
            },
        )

        # Test with unrecognised columns
        response = client.get(
            "/", params={"__visible_fields": "foobar", "__order": "id"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content,
            (
                b"No matching column found with name == foobar - the column "
                b"options are ('id', 'name', 'rating')."
            ),
        )

    def test_visible_fields_with_join(self):
        """
        Make sure that GETs with the ``__visible_fields`` parameter return the
        correct data, when using joins.
        """
        # Test 1 - should be rejected, as by default `max_joins` is 0:
        client = TestClient(PiccoloCRUD(table=Role, read_only=False))
        response = client.get(
            "/",
            params={"__visible_fields": "name,movie.name", "__order": "id"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b"Max join depth exceeded")

        # Test 2 - should work as `max_joins` is set:
        client = TestClient(
            PiccoloCRUD(table=Role, read_only=False, max_joins=1)
        )
        response = client.get(
            "/",
            params={"__visible_fields": "name,movie.name", "__order": "id"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {"movie": {"name": "Star Wars"}, "name": "Luke Skywalker"}
                ]
            },
        )

    def test_visible_fields_with_readable(self):
        """
        Make sure that GETs with the ``__visible_fields`` parameter return the
        correct data, when also used wit the ``__readable`` parameter.
        """
        client = TestClient(PiccoloCRUD(table=Role, read_only=False))

        response = client.get(
            "/",
            params={
                "__visible_fields": "name,movie",
                "__readable": "true",
                "__order": "id",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {
                        "name": "Luke Skywalker",
                        "movie_readable": "Star Wars",
                        "movie": 1,
                    }
                ]
            },
        )

    ###########################################################################

    def test_readable(self):
        """
        Make sure that bulk GETs with the ``__readable`` parameter return the
        correct data.
        """
        client = TestClient(PiccoloCRUD(table=Role, read_only=False))

        response = client.get("/", params={"__readable": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {
                        "id": 1,
                        "name": "Luke Skywalker",
                        "movie": 1,
                        "movie_readable": "Star Wars",
                    }
                ]
            },
        )

        response = client.get("/", params={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Luke Skywalker", "movie": 1}]},
        )

    def test_page_size_limit(self):
        """
        If the page size limit is exceeded, the request should be rejected.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))
        response = client.get(
            "/", params={"__page_size": PiccoloCRUD.max_page_size + 1}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(), {"error": "The page size limit has been exceeded"}
        )

    def test_offset_limit_pagination(self):
        """
        If the page size is greater than one, offset and limit is applied
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))
        response = client.get("/", params={"__page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": []})

    def test_reverse_order(self):
        """
        Make sure that descending ordering works, e.g. ``__order=-id``.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        rows = Movie.select().order_by(Movie.id, ascending=False).run_sync()

        response = client.get("/", params={"__order": "-id"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": rows})

    def test_operator_gt(self):
        """
        Test operator - greater than.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))
        response = client.get(
            "/",
            params={"__order": "id", "rating": "90", "rating__operator": "gt"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Star Wars", "rating": 93}]},
        )

    def test_operator_null(self):
        """
        Test operators - `is_null` / `not_null`.
        """
        # Create a role with a null foreign key value.
        Role(name="Joe Bloggs").save().run_sync()

        client = TestClient(PiccoloCRUD(table=Role, read_only=False))

        # Null
        response = client.get(
            "/",
            params={"movie__operator": "is_null"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 2, "movie": None, "name": "Joe Bloggs"}]},
        )

        # Not Null
        response = client.get(
            "/",
            params={"movie__operator": "not_null"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "movie": 1, "name": "Luke Skywalker"}]},
        )

        # Make sure the null operator takes precedence
        response = client.get(
            "/",
            params={"movie": 2, "movie__operator": "not_null"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "movie": 1, "name": "Luke Skywalker"}]},
        )

    def test_match(self):
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        # starts - returns data
        response = client.get(
            "/",
            params={"name": "Star", "name__match": "starts"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Star Wars", "rating": 93}]},
        )

        # starts - doesn't return data
        response = client.get(
            "/",
            params={"name": "Wars", "name__match": "starts"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": []},
        )

        # ends - returns data
        response = client.get(
            "/",
            params={"name": "Wars", "name__match": "ends"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Star Wars", "rating": 93}]},
        )

        # ends - doesn't return data
        response = client.get(
            "/",
            params={"name": "Star", "name__match": "ends"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": []},
        )

        # exact - returns data
        response = client.get(
            "/",
            params={"name": "Star Wars", "name__match": "exact"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Star Wars", "rating": 93}]},
        )

        # exact - doesn't return data
        response = client.get(
            "/",
            params={"name": "Star", "name__match": "exact"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": []},
        )

        # contains - returns data
        response = client.get(
            "/",
            params={"name": "War", "name__match": "contains"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Star Wars", "rating": 93}]},
        )

        # contains - doesn't return data
        response = client.get(
            "/",
            params={"name": "Die Hard", "name__match": "contains"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": []},
        )

        # default - contains
        response = client.get(
            "/",
            params={"name": "tar"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Star Wars", "rating": 93}]},
        )


class TestExcludeSecrets(TestCase):
    """
    Make sure that if ``exclude_secrets`` is ``True``, then values for
    ``Secret`` columns are omitted from the response.
    """

    def setUp(self):
        TopSecret.create_table(if_not_exists=True).run_sync()
        TopSecret(name="My secret", confidential="secret123").save().run_sync()

    def tearDown(self):
        TopSecret.alter().drop_table(if_exists=True).run_sync()

    def test_get_all(self):
        client = TestClient(PiccoloCRUD(table=TopSecret, exclude_secrets=True))
        response = client.get("/")
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "My secret", "confidential": None}]},
        )

        client = TestClient(
            PiccoloCRUD(table=TopSecret, exclude_secrets=False)
        )
        response = client.get("/")
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {"id": 1, "name": "My secret", "confidential": "secret123"}
                ]
            },
        )

    def test_get_single(self):
        client = TestClient(PiccoloCRUD(table=TopSecret, exclude_secrets=True))
        response = client.get("/1/")
        self.assertEqual(
            response.json(),
            {"id": 1, "name": "My secret", "confidential": None},
        )

        client = TestClient(
            PiccoloCRUD(table=TopSecret, exclude_secrets=False)
        )
        response = client.get("/1/")
        self.assertEqual(
            response.json(),
            {"id": 1, "name": "My secret", "confidential": "secret123"},
        )


class TestPost(TestCase):
    def setUp(self):
        BaseUser.create_table(if_not_exists=True).run_sync()
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        BaseUser.alter().drop_table().run_sync()
        Movie.alter().drop_table().run_sync()

    def test_success(self):
        """
        Make sure a post can create rows successfully.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        json = {"name": "Star Wars", "rating": 93}

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 201)

        self.assertEqual(Movie.count().run_sync(), 1)

        movie = Movie.objects().first().run_sync()
        self.assertEqual(movie.name, json["name"])
        self.assertEqual(movie.rating, json["rating"])

    def test_post_user_success(self):
        client = TestClient(PiccoloCRUD(table=BaseUser, read_only=False))

        json = {
            "username": "John",
            "password": "John123",
            "email": "john@test.com",
            "active": False,
            "admin": False,
            "superuser": False,
        }

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 201)

    def test_post_user_fails(self):
        client = TestClient(PiccoloCRUD(table=BaseUser, read_only=False))

        json = {
            "username": "John",
            "password": "1",
            "email": "john@test.com",
            "active": False,
            "admin": False,
            "superuser": False,
        }

        response = client.post("/", json=json)
        self.assertEqual(
            response.content, b"Error: The password is too short."
        )
        self.assertEqual(response.status_code, 400)

    def test_validation_error(self):
        """
        Make sure a post returns a validation error with incorrect or missing
        data.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        json = {"name": "Star Wars", "rating": "hello world"}

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Movie.count().run_sync(), 0)


class TestNullException(TestCase):
    """
    Make sure that if a null constraint fails, we get a useful message
    back, and not a 500 error. Implemented by the ``@db_exception_handler``
    decorator.
    """

    def setUp(self):
        Ticket.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Ticket.alter().drop_table().run_sync()

    def insert_row(self):
        self.ticket = Ticket.objects().create(code="abc123").run_sync()

    def test_post(self):
        client = TestClient(PiccoloCRUD(table=Ticket, read_only=False))

        # Test error
        response = client.post(
            "/",
            json={"code": None},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("db_error", response.json())

        # Test success
        response = client.post(
            "/",
            json={"code": "abc123"},
        )
        self.assertEqual(response.status_code, 201)

    def test_patch(self):
        self.insert_row()
        client = TestClient(PiccoloCRUD(table=Ticket, read_only=False))

        # Test error
        response = client.patch(
            f"/{self.ticket.id}/",
            json={"code": None},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("db_error", response.json())

        # Test success
        response = client.patch(
            f"/{self.ticket.id}/",
            json={"code": "xyz789"},
        )
        self.assertEqual(response.status_code, 200)

    def test_put(self):
        self.insert_row()
        client = TestClient(PiccoloCRUD(table=Ticket, read_only=False))

        # Test error
        response = client.put(
            f"/{self.ticket.id}/",
            json={
                "code": None,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("db_error", response.json())

        # Test success
        response = client.put(
            f"/{self.ticket.id}/",
            json={
                "code": "xyz789",
            },
        )
        self.assertEqual(response.status_code, 204)


class TestUniqueException(TestCase):
    """
    Make sure that if a unique constraint fails, we get a useful message
    back, and not a 500 error. Implemented by the ``@db_exception_handler``
    decorator.
    """

    def setUp(self):
        Cinema.create_table(if_not_exists=True).run_sync()

        self.cinema_1 = (
            Cinema.objects()
            .create(
                name="Odeon",
                address="Leicester Square, London",
            )
            .run_sync()
        )

        self.cinema_2 = (
            Cinema.objects()
            .create(
                name="Grauman's Chinese Theatre",
                address="6925 Hollywood Boulevard, Hollywood",
            )
            .run_sync()
        )

    def tearDown(self):
        Cinema.alter().drop_table().run_sync()

    def test_post(self):
        client = TestClient(PiccoloCRUD(table=Cinema, read_only=False))

        # Test error
        response = client.post(
            "/",
            json={"name": "Odeon 2", "address": self.cinema_1.address},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("db_error", response.json())

        # Test success
        response = client.post(
            "/",
            json={"name": "Odeon 2", "address": "A new address"},
        )
        self.assertEqual(response.status_code, 201)

    def test_patch(self):
        client = TestClient(PiccoloCRUD(table=Cinema, read_only=False))

        # Test error
        response = client.patch(
            f"/{self.cinema_1.id}/",
            json={"address": self.cinema_2.address},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("db_error", response.json())

        # Test success
        response = client.patch(
            f"/{self.cinema_1.id}/",
            json={"address": "A new address"},
        )
        self.assertEqual(response.status_code, 200)

    def test_put(self):
        client = TestClient(PiccoloCRUD(table=Cinema, read_only=False))

        # Test error
        response = client.put(
            f"/{self.cinema_1.id}/",
            json={
                "name": self.cinema_1.name,
                "address": self.cinema_2.address,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("db_error", response.json())

        # Test success
        response = client.put(
            f"/{self.cinema_1.id}/",
            json={
                "name": "New cinema",
                "address": "A new address",
            },
        )
        self.assertEqual(response.status_code, 204)


class TestForeignKeyViolationException(TestCase):
    """
    Make sure that if a foreign key violation is raised, we get a useful
    message back, and not a 500 error. Implemented by the
    ``@db_exception_handler`` decorator.
    """

    def setUp(self):
        class Director(Table):
            name = Varchar()

        class Movie(Table):
            name = Varchar()
            director = ForeignKey(
                references=Director, on_delete=OnDelete.restrict
            )

        self.table_classes = (Director, Movie)

        create_db_tables_sync(*self.table_classes, if_not_exists=True)

        self.director = Director({Director.name: "George Lucas"})
        self.director.save().run_sync()

        Movie(
            {Movie.director: self.director, Movie.name: "Star Wars"}
        ).save().run_sync()

    def tearDown(self):
        drop_db_tables_sync(*self.table_classes)

    def test_delete(self):
        director = self.director

        client = TestClient(
            PiccoloCRUD(table=self.director.__class__, read_only=False)
        )

        # Test error
        response = client.delete(f"/{director.id}/")
        self.assertEqual(response.status_code, 422)
        self.assertIn("db_error", response.json())


class TestGet(TestCase):
    def setUp(self):
        for table in (Movie, Role):
            table.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        for table in (Role, Movie):
            table.alter().drop_table().run_sync()

    def test_get(self):
        """
        Make sure a get can return a row successfully.
        """
        client = TestClient(PiccoloCRUD(table=Role, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        role = Role(name="Luke Skywalker", movie=movie.id)
        role.save().run_sync()

        response = client.get(f"/{role.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": role.id, "name": "Luke Skywalker", "movie": movie.id},
        )

        response = client.get(f"/{role.id}/", params={"__readable": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": role.id,
                "name": "Luke Skywalker",
                "movie": movie.id,
                "movie_readable": "Star Wars",
            },
        )

        response = client.get("/123/")
        self.assertEqual(response.status_code, 404)

    def test_get_visible_fields(self):
        """
        Make sure a get can return a row successfully with the
        ``__visible_fields`` parameter.
        """
        client = TestClient(PiccoloCRUD(table=Role, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        role = Role(name="Luke Skywalker", movie=movie.id)
        role.save().run_sync()

        response = client.get(
            f"/{role.id}/", params={"__visible_fields": "name"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "name": "Luke Skywalker",
            },
        )

        # Test with unrecognised columns
        response = client.get(
            f"/{role.id}/", params={"__visible_fields": "foobar"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content,
            (
                b"No matching column found with name == foobar - the column "
                b"options are ('id', 'movie', 'name')."
            ),
        )

    def test_get_visible_fields_with_join(self):
        """
        Make sure a get can return a row successfully
        with the ``__visible_fields`` parameter, when using joins.
        """
        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        role = Role(name="Luke Skywalker", movie=movie.id)
        role.save().run_sync()

        # Test 1 - should be rejected, as by default `max_joins` is 0:
        client = TestClient(PiccoloCRUD(table=Role, read_only=False))
        response = client.get(
            f"/{role.id}/",
            params={"__visible_fields": "name,movie.name"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b"Max join depth exceeded")

        # Test 2 - should work as `max_joins` is set:
        client = TestClient(
            PiccoloCRUD(table=Role, read_only=False, max_joins=1)
        )

        response = client.get(
            f"/{role.id}/", params={"__visible_fields": "name,movie.name"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "name": "Luke Skywalker",
                "movie": {
                    "name": "Star Wars",
                },
            },
        )

    def test_get_visible_fields_with_join_readable(self):
        """
        Make sure a get can return a row successfully with the
        ``__visible_fields`` parameter, when using joins and readable.
        """
        client = TestClient(
            PiccoloCRUD(table=Role, read_only=False, max_joins=1)
        )

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        role = Role(name="Luke Skywalker", movie=movie.id)
        role.save().run_sync()

        response = client.get(
            f"/{role.id}/",
            params={
                "__visible_fields": "id,name,movie.name",
                "__readable": "true",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": 1,
                "name": "Luke Skywalker",
                "movie_readable": "Star Wars",
                "movie": {
                    "name": "Star Wars",
                },
            },
        )

    def test_get_404(self):
        """
        A 404 should be returned if there's no matching row.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        json = {"name": "Star Wars", "rating": "hello world"}

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Movie.count().run_sync(), 0)


class TestBulkDelete(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_no_bulk_delete(self):
        """
        Make sure that deletes aren't allowed when ``allow_bulk_delete`` is
        False.
        """
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, allow_bulk_delete=False)
        )

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.delete("/")
        self.assertEqual(response.status_code, 405)

        movie_count = Movie.count().run_sync()
        self.assertEqual(movie_count, 1)

    def test_bulk_delete(self):
        """
        Make sure that bulk deletes are only allowed is allow_bulk_delete is
        True.
        """
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, allow_bulk_delete=True)
        )

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.delete("/")
        self.assertEqual(response.status_code, 204)

        movie_count = Movie.count().run_sync()
        self.assertEqual(movie_count, 0)

    def test_bulk_delete_filtering(self):
        """
        Make sure filtering works with bulk deletes.
        """
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, allow_bulk_delete=True)
        )

        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=90),
        ).run_sync()

        response = client.delete("/?name=Star%20Wars")
        self.assertEqual(response.status_code, 204)

        movies = Movie.select().run_sync()
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0]["name"], "Lord of the Rings")

    def test_read_only(self):
        """
        In read_only mode, no HTTP verbs should be allowed which modify data.
        """
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=True, allow_bulk_delete=True)
        )

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.delete("/")
        self.assertEqual(response.status_code, 405)

        movie_count = Movie.count().run_sync()
        self.assertEqual(movie_count, 1)


class TestNew(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_new(self):
        """
        When calling the new endpoint, the defaults for a new row are returned.
        It's used when building a UI on top of the API.
        """
        client = TestClient(PiccoloCRUD(table=Movie))

        response = client.get("/new/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"id": None, "name": "", "rating": 0}
        )

    def test_email(self):
        """
        Make sure that `Email` column types work correctly.

        https://github.com/piccolo-orm/piccolo_api/issues/184

        """
        client = TestClient(PiccoloCRUD(table=Studio))

        response = client.get("/new/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": None,
                "name": "",
                # If the default isn't a valid email, make sure it's set to
                # None
                "contact_email": None,
                # If the default is valid email, then make sure it's still
                # present.
                "booking_email": "booking@studio.com",
            },
        )


class TestMalformedQuery(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_malformed_query(self):
        """
        A malformed query (for example, an unrecognised column name) should be
        handled gracefully, and return an error status code.
        """
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, allow_bulk_delete=True)
        )

        response = client.get("/", params={"foobar": "1"})
        self.assertEqual(response.status_code, 400)

        response = client.get("/count/", params={"foobar": "1"})
        self.assertEqual(response.status_code, 400)

        response = client.delete("/", params={"foobar": "1"})
        self.assertEqual(response.status_code, 400)


class TestIncorrectVerbs(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_incorrect_verbs(self):
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, allow_bulk_delete=True)
        )

        response = client.patch("/", params={})
        self.assertEqual(response.status_code, 405)


class TestParseParams(TestCase):
    def test_parsing(self):
        app = PiccoloCRUD(table=Movie)

        parsed_1 = app._parse_params(
            QueryParams("tags=horror&tags=scifi&rating=90")
        )
        self.assertEqual(
            parsed_1, {"tags": ["horror", "scifi"], "rating": "90"}
        )

        parsed_2 = app._parse_params(
            QueryParams("tags[]=horror&tags[]=scifi&rating=90")
        )
        self.assertEqual(
            parsed_2, {"tags": ["horror", "scifi"], "rating": "90"}
        )


class RangeHeaders(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_plural_name(self):
        """
        Make sure the content-range header responds correctly for empty rows
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
            )
        )

        response = client.get(
            "/?__range_header=true&__range_header_name=movies"
        )
        self.assertEqual(response.status_code, 200)
        # Make sure the content is correct:
        response_json = response.json()
        self.assertEqual(0, len(response_json["rows"]))
        self.assertEqual(response.headers.get("Content-Range"), "movies 0-0/0")

    def test_false_range_header_param(self):
        """
        Make sure that __range_header=false is supported
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
            )
        )

        response = client.get("/?__range_header=false")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Range"), None)

    def test_empty_list(self):
        """
        Make sure the content-range header responds correctly for empty rows
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        response = client.get("/?__range_header=true")
        self.assertEqual(response.status_code, 200)
        # Make sure the content is correct:
        response_json = response.json()
        self.assertEqual(0, len(response_json["rows"]))
        self.assertEqual(response.headers.get("Content-Range"), "movie 0-0/0")

    def test_unpaged_ranges(self):
        """
        Make sure the content-range header responds
        correctly for unpaged results
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()
        movie2 = Movie(name="Blade Runner", rating=94)
        movie2.save().run_sync()

        response = client.get("/?__range_header=true")
        self.assertEqual(response.status_code, 200)
        # Make sure the content is correct:
        response_json = response.json()
        self.assertEqual(2, len(response_json["rows"]))
        self.assertEqual(
            str(2), response.headers.get("Content-Range").split("/")[1]
        )
        self.assertEqual(response.headers.get("Content-Range"), "movie 0-1/2")

    def test_page_sized_results(self):
        """
        Make sure the content-range header responds
        correctly requests with page_size
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()
        movie2 = Movie(name="Blade Runner", rating=94)
        movie2.save().run_sync()
        movie3 = Movie(name="The Godfather", rating=95)
        movie3.save().run_sync()

        response = client.get("/?__page_size=1&__range_header=true")
        self.assertEqual(response.headers.get("Content-Range"), "movie 0-0/3")

        response = client.get("/?__page_size=1&__page=2&__range_header=true")
        self.assertEqual(response.headers.get("Content-Range"), "movie 1-1/3")

        response = client.get("/?__page_size=1&__page=2&__range_header=true")
        self.assertEqual(response.headers.get("Content-Range"), "movie 1-1/3")

        response = client.get("/?__page_size=99&__page=1&__range_header=true")
        self.assertEqual(response.headers.get("Content-Range"), "movie 0-2/3")


class TestOrderBy(TestCase):
    def test_eq(self):
        # Same column, same ascending
        self.assertEqual(
            OrderBy(column=Movie.name, ascending=True),
            OrderBy(column=Movie.name, ascending=True),
        )

        # Same column, different ascending
        self.assertNotEqual(
            OrderBy(column=Movie.name, ascending=True),
            OrderBy(column=Movie.name, ascending=False),
        )

        # Different column, same ascending
        self.assertNotEqual(
            OrderBy(column=Movie.name, ascending=True),
            OrderBy(column=Movie.id, ascending=True),
        )

    def test_to_dict(self):
        self.assertDictEqual(
            OrderBy(column=Movie.name, ascending=True).to_dict(),
            {"column": "name", "ascending": True},
        )

        self.assertDictEqual(
            OrderBy(column=Role.movie.name, ascending=True).to_dict(),
            {"column": "movie.name", "ascending": True},
        )

        self.assertDictEqual(
            OrderBy(column=Role.movie.name, ascending=False).to_dict(),
            {"column": "movie.name", "ascending": False},
        )
