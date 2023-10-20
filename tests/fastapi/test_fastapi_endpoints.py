import sys
import typing as t
from unittest import TestCase

import pytest
from fastapi import FastAPI
from piccolo.columns import ForeignKey, Integer, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIWrapper, _get_type


class Movie(Table):
    name = Varchar(length=100)
    rating = Integer()

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.name])


class Role(Table):
    movie = ForeignKey(Movie)
    name = Varchar(length=100)


app = FastAPI()


FastAPIWrapper(
    root_url="/movies/",
    fastapi_app=app,
    piccolo_crud=PiccoloCRUD(
        table=Movie, read_only=False, allow_bulk_delete=True
    ),
)

FastAPIWrapper(
    root_url="/roles/",
    fastapi_app=app,
    piccolo_crud=PiccoloCRUD(
        table=Role, read_only=False, allow_bulk_delete=True, max_joins=1
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
        Movie(name="Star Wars", rating=93).save().run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_get(self):
        client = TestClient(app)
        response = client.get("/movies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": 1, "name": "Star Wars", "rating": 93}]},
        )

    def test_get_single(self):
        client = TestClient(app)
        response = client.get("/movies/1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": 1, "name": "Star Wars", "rating": 93},
        )

    def test_count(self):
        client = TestClient(app)
        response = client.get("/movies/count/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"count": 1, "page_size": 15},
        )

    def test_schema(self):
        client = TestClient(app)
        response = client.get("/movies/schema/")
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
                "title": "MovieIn",
                "type": "object",
            },
        )

    def test_schema_joins(self):
        client = TestClient(app)
        response = client.get("/roles/schema/")
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

    def test_get_ids(self):
        client = TestClient(app)
        response = client.get("/movies/ids/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"1": "Star Wars"})

    def test_new(self):
        client = TestClient(app)
        response = client.get("/movies/new/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": None, "name": "", "rating": 0},
        )

    def test_references(self):
        client = TestClient(app)
        response = client.get("/movies/references/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"references": [{"columnName": "movie", "tableName": "role"}]},
        )

    def test_delete(self):
        client = TestClient(app)
        response = client.delete("/movies/1/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def test_allow_bulk_delete(self):
        client = TestClient(app)
        response = client.delete("/movies/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def test_post(self):
        client = TestClient(app)
        response = client.post(
            "/movies/", json={"name": "Star Wars", "rating": 93}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), [{"id": 2}])

    def test_put(self):
        client = TestClient(app)
        response = client.put(
            "/movies/1/", json={"name": "Star Wars", "rating": 95}
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def test_patch(self):
        client = TestClient(app)
        response = client.patch("/movies/1/", json={"rating": 90})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"name": "Star Wars", "rating": 90})

        response = client.get("/movies/1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"id": 1, "name": "Star Wars", "rating": 90}
        )


class TestGetType(TestCase):
    def test_get_type(self):
        """
        If we pass in an optional type, it should return the non-optional type.
        """
        # Should return the underlying type, as they're all optional:
        self.assertIs(_get_type(t.Optional[str]), str)
        self.assertIs(_get_type(t.Optional[t.List[str]]), t.List[str])
        self.assertIs(_get_type(t.Union[str, None]), str)

        # Should be returned as is, because it's not optional:
        self.assertIs(_get_type(t.List[str]), t.List[str])

    @pytest.mark.skipif(
        sys.version_info < (3, 10), reason="Union syntax not available"
    )
    def test_new_union_syntax(self):
        """
        Make sure it works with the new syntax added in Python 3.10.
        """
        self.assertIs(_get_type(str | None), str)  # type: ignore
        self.assertIs(_get_type(None | str), str)  # type: ignore
