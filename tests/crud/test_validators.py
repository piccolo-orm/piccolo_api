import typing as t
from dataclasses import dataclass
from unittest import TestCase

from piccolo.columns import Integer, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from starlette.exceptions import ExceptionMiddleware, HTTPException
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import PiccoloCRUD, Validators


class Movie(Table):
    name = Varchar(length=100, required=True)
    rating = Integer()

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])


@dataclass
class Scenario:
    validators: t.List[t.Callable]
    status_code: int
    content: bytes


class TestValidators(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_validators(self):
        """
        Make sure that bulk GETs return the correct data.
        """

        def validator_1(*args, **kwargs):
            raise ValueError("Error!")

        def validator_2(*args, **kwargs):
            raise HTTPException(status_code=401, detail="Denied!")

        for scenario in [
            Scenario(
                validators=[validator_1],
                status_code=400,
                content=b"Validation error",
            ),
            Scenario(
                validators=[validator_2],
                status_code=401,
                content=b"Denied!",
            ),
        ]:
            client = TestClient(
                ExceptionMiddleware(
                    PiccoloCRUD(
                        table=Movie,
                        read_only=False,
                        validators=Validators(get_all=scenario.validators),
                    )
                )
            )

            response = client.get("/")
            self.assertEqual(response.status_code, scenario.status_code)
            self.assertEqual(response.content, scenario.content)
