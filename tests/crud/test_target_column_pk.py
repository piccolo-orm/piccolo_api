from unittest import TestCase

from piccolo.columns.column_types import ForeignKey, Varchar
from piccolo.table import Table
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import PiccoloCRUD


class Serie(Table):
    name = Varchar(length=100, unique=True)


class Review(Table):
    reviewer = Varchar()
    serie = ForeignKey(Serie, target_column=Serie.name)


class TestTargetPK(TestCase):
    """
    Make sure PiccoloCRUD works with Tables with a custom primary key column.
    """

    def setUp(self):
        Serie.create_table(if_not_exists=True).run_sync()
        Review.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Review.alter().drop_table().run_sync()
        Serie.alter().drop_table().run_sync()

    def test_target_column_pk(self):
        serie = Serie(name="Devs")
        serie.save().run_sync()
        Review(reviewer="John Doe", serie=serie["name"]).save().run_sync()
        review = Review.select(Review.serie.id).first().run_sync()

        self.client = TestClient(PiccoloCRUD(table=Serie, read_only=False))
        response = self.client.get("/Devs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], review["serie.id"])
