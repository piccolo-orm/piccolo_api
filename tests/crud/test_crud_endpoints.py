import json
from unittest import TestCase

from piccolo.engine.sqlite import SQLiteEngine
from piccolo.table import Table
from piccolo.columns import Varchar, Integer
from piccolo.columns.readable import Readable
from piccolo_api.crud.endpoints import PiccoloCRUD, GreaterThan

from starlette.testclient import TestClient


engine = SQLiteEngine(path="piccolo_api_tests.sqlite")


class Movie(Table, db=engine):  # type: ignore
    name = Varchar(length=100)
    rating = Integer()

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])


app = PiccoloCRUD(table=Movie)


class TestParams(TestCase):
    def test_split_params(self):
        """
        Make sure the HTTP parameters are parsed correctly.
        """
        params = {"age__operator": "gt", "age": 25}
        split_params = PiccoloCRUD._split_params(params)
        self.assertEqual(split_params.operators["age"], GreaterThan)
        self.assertEqual(
            split_params.fields, {"age": 25},
        )
        self.assertEqual(
            split_params.include_readable, False,
        )

        params = {"__readable": "true"}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.include_readable, True,
        )

        params = {"__page_size": 5}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.page_size, 5,
        )

        params = {"__page": 2}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.page, 2,
        )


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
        app = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        rating = 93
        movie = Movie(name="Star Wars", rating=rating)
        movie.save().run_sync()

        new_name = "Star Wars: A New Hope"

        response = app.patch(f"/{movie.id}/", json={"name": new_name})
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
        app = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = app.patch(f"/{movie.id}/", json={"foo": "bar"})
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
        app = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = app.get("/ids/")
        self.assertTrue(response.status_code == 200)

        # Make sure the content is correct:
        response_json = response.json()
        self.assertTrue(response_json[str(movie.id)] == "Star Wars")


class TestCount(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_get_count(self):
        """
        Make sure the correct count is returned.
        """
        app = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = app.get("/count/")
        self.assertTrue(response.status_code == 200)

        # Make sure the count is correct:
        response_json = response.json()
        self.assertTrue(response_json["count"] == 1)


class TestEndpoints(TestCase):
    def test_bulk_delete(self):
        """
        Make sure that bulk deletes are only allowed is allow_bulk_delete is
        True.
        """
        pass

    def test_read_only(self):
        """
        In read_only mode, no HTTP verbs should be allowed which modify data.
        """
        pass
