from unittest import TestCase

from fastapi import FastAPI
from piccolo.engine.sqlite import SQLiteEngine
from piccolo.table import Table
from piccolo.columns import Varchar, Integer
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIWrapper


engine = SQLiteEngine(path="piccolo_api_tests.sqlite")


class Movie(Table, db=engine):  # type: ignore
    name = Varchar(length=100)
    rating = Integer()


app = FastAPI()


FastAPIWrapper(
    root_url="/movies/",
    fastapi_app=app,
    piccolo_crud=PiccoloCRUD(
        table=Movie, read_only=False, allow_bulk_delete=True
    ),
)


class TestOpenAPI(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_200_response(self):
        client = TestClient(app)

        response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)


class TestResponses(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_get_responses(self):
        Movie(name="Star Wars", rating=93).save().run_sync()

        client = TestClient(app)

        response = client.get("/movies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Star Wars", "rating": 93}]},
        )

        response = client.get("/movies/1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"id": 1, "name": "Star Wars", "rating": 93},
        )
