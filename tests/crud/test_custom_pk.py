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

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_get_ids(self):
        movie = Movie.objects().create(name="Star Wars").run_sync()
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))
        response = client.get("/ids/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {str(movie.id): str(movie.id)})

    def test_get_list(self):
        movie = Movie.objects().create(name="Star Wars").run_sync()
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "rows": [
                    {
                        "id": str(movie.id),
                        "name": movie.name,
                        "rating": movie.rating,
                    }
                ]
            },
        )
