import json
from unittest import TestCase

from piccolo.engine.sqlite import SQLiteEngine
from piccolo.table import Table
from piccolo.columns import Varchar, Integer
from piccolo_api.crud.endpoints import PiccoloCRUD, GreaterThan

from starlette.testclient import TestClient


engine = SQLiteEngine(path="piccolo_api_tests.sqlite")


class Movie(Table, db=engine):  # type: ignore
    name = Varchar(length=100)
    rating = Integer()


app = PiccoloCRUD(table=Movie)


class TestEndpoints(TestCase):
    def test_split_params(self):
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

    def test_patch(self):
        """
        Make sure a patch modifies the underlying database, and returns the
        new row data.
        """
        app = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        Movie.create_table().run_sync()

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

        Movie.alter().drop_table().run_sync()
