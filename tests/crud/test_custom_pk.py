from unittest import TestCase

from piccolo.columns.column_types import UUID, Integer, Varchar
from piccolo.table import Table
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import PiccoloCRUD


class Movie(Table):
    id = UUID(primary_key=True)
    name = Varchar(length=100, required=True)
    rating = Integer()


class TestCustomPK(TestCase):
    """
    Make sure PiccoloCRUD works with Tables with a custom primary key column.
    """

    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()
        self.movie = Movie.objects().create(name="Star Wars").run_sync()
        self.client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_get_ids(self):
        response = self.client.get("/ids/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {str(self.movie.id): str(self.movie.id)}
        )

    def test_get_list(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {
                        "id": str(self.movie.id),
                        "name": self.movie.name,
                        "rating": self.movie.rating,
                    }
                ]
            },
        )

    def test_get_single(self):
        response = self.client.get(f"/{str(self.movie.id)}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": str(self.movie.id),
                "name": self.movie.name,
                "rating": self.movie.rating,
            },
        )

    def test_post(self):
        Movie.delete(force=True).run_sync()
        response = self.client.post(
            "/", json={"name": "Lord of the Rings", "rating": 1000}
        )
        self.assertEqual(response.status_code, 201)

        movie = Movie.select(Movie.name, Movie.rating).first().run_sync()
        self.assertEqual(movie, {"name": "Lord of the Rings", "rating": 1000})

    def test_delete(self):
        response = self.client.delete(f"/{self.movie.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Movie.count().run_sync(), 0)

    def test_patch(self):
        response = self.client.patch(
            f"/{self.movie.id}/", json={"rating": 2000}
        )
        self.assertEqual(response.status_code, 200)
        movie = Movie.select().first().run_sync()
        self.assertEqual(
            movie, {"id": self.movie.id, "name": "Star Wars", "rating": 2000}
        )

    def test_invalid_id(self):
        response = self.client.get("/abc123/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b"The ID is invalid")
