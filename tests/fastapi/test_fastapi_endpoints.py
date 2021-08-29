import json
from unittest import TestCase

from fastapi import FastAPI
from piccolo.columns import Integer, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIWrapper


class Movie(Table):
    name = Varchar(length=100)
    rating = Integer()

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.name])


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
        Movie(id=1, name="Star Wars", rating=93).save().run_sync()

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
            response.json(),
            {"id": 1, "name": "Star Wars", "rating": 93},
        )

        response = client.get("/movies/count/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"count": 1, "page_size": 15},
        )

        response = client.get("/movies/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "title": "MovieIn",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Name",
                        "extra": {"help_text": None, "choices": None},
                        "maxLength": 100,
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
                "help_text": None,
            },
        )

        response = client.get("/movies/ids/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"1": "Star Wars"})

        response = client.get("/movies/new/")
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(
            response_json["name"],
            "",
        )
        self.assertEqual(
            response_json["rating"],
            0,
        )

        response = client.get("/movies/references/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"references": []})

        response = client.delete("/movies/?id=1")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

        response = client.post(
            "/movies/", json={"name": "Star Wars", "rating": 93}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), [{"id": 1}])

        response = client.put(
            "/movies/1/", json={"name": "Star Wars", "rating": 95}
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

        response = client.patch("/movies/1/", json={"rating": 90})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), json.dumps({"name": "Star Wars", "rating": 90})
        )  # Revise

        response = client.get("/movies/1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"id": 1, "name": "Star Wars", "rating": 90}
        )
