import typing as t
from unittest import TestCase

from fastapi import FastAPI, Request
from piccolo.columns import Integer, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from piccolo_api.crud.cursor_pagination import CursorPagination


class Movie(Table):
    name = Varchar(length=100, required=True)
    rating = Integer()

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])


app = FastAPI()


@app.get("/movies/")
def movies(
    request: Request,
    __cursor: str,
    __previous: t.Optional[str] = None,
):
    try:
        cursor = request.query_params["__cursor"]
        paginator = CursorPagination(cursor=cursor, page_size=1, order_by="id")
        rows_result, headers_result = paginator.get_cursor_rows(Movie, request)
        rows = rows_result.run_sync()
        headers = headers_result
        response = JSONResponse(
            {"rows": rows[::-1]},
            headers={
                "next_cursor": headers["cursor"],
            },
        )
    except KeyError:
        cursor = request.query_params["__cursor"]
        paginator = CursorPagination(cursor=cursor, page_size=1, order_by="id")
        rows_result, headers_result = paginator.get_cursor_rows(Movie, request)
        rows = rows_result.run_sync()
        headers = headers_result
        response = JSONResponse(
            {"rows": rows},
            headers={
                "next_cursor": headers["cursor"],
            },
        )
    return response


class TestCursorPaginationAsc(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_cursor_pagination_asc(self):
        """
        If cursor is applied
        """
        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=90),
        ).run_sync()

        client = TestClient(app)
        response = client.get("/movies/", params={"__cursor": ""})
        self.assertTrue(response.status_code, 200)
        self.assertEqual(response.headers["next_cursor"], "Mg==")
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {"id": 1, "name": "Star Wars", "rating": 93},
                ]
            },
        )

    def test_cursor_pagination_asc_previous(self):
        """
        If cursor ad previous is applied
        """
        Movie.insert(
            Movie(name="Star Wars", rating=93),
            Movie(name="Lord of the Rings", rating=90),
        ).run_sync()

        client = TestClient(app)
        response = client.get(
            "/movies/", params={"__cursor": "Mg==", "__previous": "yes"}
        )
        self.assertTrue(response.status_code, 200)
        self.assertEqual(response.headers["next_cursor"], "")
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {"id": 1, "name": "Star Wars", "rating": 93},
                ]
            },
        )
