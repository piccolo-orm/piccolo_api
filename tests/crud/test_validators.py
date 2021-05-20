from unittest import TestCase

from piccolo.table import Table
from piccolo.columns import Varchar, Integer, ForeignKey
from piccolo.columns.readable import Readable
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import PiccoloCRUD, Validators


class Movie(Table):
    name = Varchar(length=100, required=True)
    rating = Integer()

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])


class Role(Table):
    movie = ForeignKey(Movie)
    name = Varchar(length=100)


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

    def test_get_all(self):
        """
        Make sure that bulk GETs return the correct data.
        """

        def validator(*args, **kwargs):
            raise ValueError("Error!")

        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                validators=Validators(get_all=[validator]),
            )
        )

        rows = Movie.select().order_by(Movie.id).run_sync()

        response = client.get("/", params={"__order": "id"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": rows})
