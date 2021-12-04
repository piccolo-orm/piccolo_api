import json
from enum import Enum
from unittest import TestCase

from piccolo.columns import ForeignKey, Integer, Secret, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from starlette.datastructures import QueryParams
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import GreaterThan, PiccoloCRUD


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


class TestParams(TestCase):
    def test_split_params(self):
        """
        Make sure the HTTP parameters are parsed correctly.
        """
        params = {"age__operator": "gt", "age": 25}
        split_params = PiccoloCRUD._split_params(params)
        self.assertEqual(split_params.operators["age"], GreaterThan)
        self.assertEqual(
            split_params.fields,
            {"age": 25},
        )
        self.assertEqual(
            split_params.include_readable,
            False,
        )

        params = {"__readable": "true"}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.include_readable,
            True,
        )

        params = {"__page_size": 5}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.page_size,
            5,
        )

        params = {"__page": 2}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.page,
            2,
        )

        params = {"__page": "one"}
        split_params = PiccoloCRUD._split_params(params)
        self.assertEqual(split_params.page, 1)

        params = {"__page_size": "one"}
        split_params = PiccoloCRUD._split_params(params)
        self.assertEqual(split_params.page_size, None)

        params = {"__visible_fields": "id,name"}
        split_params = PiccoloCRUD._split_params(params)
        self.assertEqual(split_params.visible_fields, "id,name")


class TestPatch(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
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
        self.assertTrue(response.status_code == 200)

        # Make sure the row is returned:
        response_json = json.loads(response.json())
        self.assertTrue(response_json["name"] == new_name)
        self.assertTrue(response_json["rating"] == rating)

        # Make sure the underlying database row was changed:
        movies = Movie.select().run_sync()
        self.assertTrue(len(movies) == 1)
        self.assertTrue(movies[0]["name"] == new_name)

    def test_patch_fails(self):
        """
        Make sure a patch containing the wrong columns is rejected.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.patch(f"/{movie.id}/", json={"foo": "bar"})
        self.assertTrue(response.status_code == 400)


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
        self.assertTrue(response.status_code == 200)

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
            self.assertTrue(response.status_code == 200)

            # Make sure the content is correct:
            response_json = response.json()
            self.assertEqual(len(response_json), 1)
            self.assertTrue("Star Wars" in response_json.values())

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
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.json(), {"1": "Star Wars"})

        # Make sure only valid limit values are accepted.
        response = client.get("/ids/?limit=abc")
        self.assertEqual(response.status_code, 400)

        # Make sure only valid offset values are accepted.
        response = client.get("/ids/?offset=abc")
        self.assertEqual(response.status_code, 400)

        # Test with offset
        response = client.get("/ids/?limit=1&offset=1")
        self.assertTrue(response.status_code == 200)
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
        self.assertTrue(response.status_code == 200)

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
        self.assertTrue(response.status_code == 200)

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
        self.assertTrue(response.status_code == 200)

        self.assertEqual(
            response.json(),
            {
                "title": "MovieIn",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Name",
                        "maxLength": 100,
                        "extra": {"help_text": None, "choices": None},
                        "nullable": False,
                        "type": "string",
                    },
                    "rating": {
                        "title": "Rating",
                        "extra": {"help_text": None, "choices": None},
                        "nullable": False,
                        "type": "integer",
                    },
                },
                "required": ["name"],
                "help_text": None,
                "fields": [
                    "id",
                    "name",
                    "rating",
                ],
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
        self.assertTrue(response.status_code == 200)

        self.assertEqual(
            response.json(),
            {
                "title": "ReviewIn",
                "type": "object",
                "properties": {
                    "score": {
                        "title": "Score",
                        "extra": {
                            "help_text": None,
                            "choices": {
                                "bad": {"display_name": "Bad", "value": 1},
                                "average": {
                                    "display_name": "Average",
                                    "value": 2,
                                },
                                "good": {"display_name": "Good", "value": 3},
                                "great": {"display_name": "Great", "value": 4},
                            },
                        },
                        "nullable": False,
                        "type": "integer",
                    }
                },
                "help_text": None,
                "fields": [
                    "id",
                    "score",
                ],
            },
        )

    def test_get_schema_with_joins(self):
        """
        Make sure that if a Table has columns with joins specified, they
        appear in the schema.
        """
        client = TestClient(PiccoloCRUD(table=Role, read_only=False))

        response = client.get("/schema/")
        self.assertTrue(response.status_code == 200)

        self.assertEqual(
            response.json(),
            {
                "title": "RoleIn",
                "type": "object",
                "properties": {
                    "movie": {
                        "title": "Movie",
                        "extra": {
                            "foreign_key": True,
                            "to": "movie",
                            "help_text": None,
                            "choices": None,
                        },
                        "nullable": True,
                        "type": "integer",
                    },
                    "name": {
                        "title": "Name",
                        "extra": {"help_text": None, "choices": None},
                        "nullable": False,
                        "maxLength": 100,
                        "type": "string",
                    },
                },
                "help_text": None,
                "fields": [
                    "id",
                    "movie",
                    "name",
                    "movie.id",
                    "movie.movie",
                    "movie.name",
                ],
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
        self.assertTrue(response.status_code == 204)

        self.assertTrue(Movie.count().run_sync() == 0)

    def test_delete_404(self):
        """
        Should get a 404 if a matching row doesn't exist.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        response = client.delete("/123/")
        self.assertTrue(response.status_code == 404)


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
        self.assertTrue(response.status_code == 204)

        self.assertTrue(Movie.count().run_sync() == 1)

    def test_put_new(self):
        """
        We expect a 404 - we don't allow PUT requests to create new resources.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        response = client.put("/123/")
        self.assertTrue(response.status_code == 404)


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

        # Test with unrecognised columns
        response = client.get(
            "/", params={"__visible_fields": "foobar", "__order": "id"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, b"No matching column found with name == foobar"
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
        self.assertTrue(response.status_code, 403)
        self.assertEqual(
            response.json(), {"error": "The page size limit has been exceeded"}
        )

    def test_offset_limit_pagination(self):
        """
        If the page size is greater than one, offset and limit is applied
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))
        response = client.get("/", params={"__page": 2})
        self.assertTrue(response.status_code, 403)
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

    def test_operator(self):
        """
        Test filters - greater than.
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
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_post(self):
        """
        Make sure a post can create rows successfully.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        json = {"name": "Star Wars", "rating": 93}

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 201)

        self.assertTrue(Movie.count().run_sync() == 1)

        movie = Movie.objects().first().run_sync()
        self.assertTrue(movie.name == json["name"])
        self.assertTrue(movie.rating == json["rating"])

    def test_post_error(self):
        """
        Make sure a post returns a validation error with incorrect or missing
        data.
        """
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        json = {"name": "Star Wars", "rating": "hello world"}

        response = client.post("/", json=json)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Movie.count().run_sync() == 0)


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
            response.content, b"No matching column found with name == foobar"
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
        self.assertTrue(Movie.count().run_sync() == 0)


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
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=True, allow_bulk_delete=True)
        )

        Movie(name="Star Wars", rating=93).save().run_sync()

        response = client.get("/new/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"id": None, "name": "", "rating": 0}
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
