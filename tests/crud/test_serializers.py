from unittest import TestCase

from piccolo.table import Table
from piccolo.columns import Varchar
from pydantic import ValidationError

from piccolo_api.crud.serializers import create_pydantic_model


class TestVarchar(TestCase):
    def test_varchar_length(self):
        class Director(Table):
            name = Varchar(length=10)

        pydantic_model = create_pydantic_model(table=Director)

        with self.assertRaises(ValidationError):
            pydantic_model(name="This is a really long name")

        pydantic_model(name="short name")
