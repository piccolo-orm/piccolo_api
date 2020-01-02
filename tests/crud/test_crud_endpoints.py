from unittest import TestCase

from piccolo_api.crud.endpoints import PiccoloCRUD, GreaterThan


class TestEndpoints(TestCase):
    def test_split_params(self):
        params = {"age__operator": "gt", "age": 25}
        split_params = PiccoloCRUD._split_params(params)
        self.assertEqual(split_params.operators["age"], GreaterThan)
        self.assertEqual(
            split_params.fields, {"age": 25},
        )
        self.assertEqual(
            split_params.include_readable, False,
        )

        params = {"__readable": "true"}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.include_readable, True,
        )

        params = {"__page_size": 5}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.page_size, 5,
        )

        params = {"__page": 2}
        split_params = PiccoloCRUD._split_params(params)

        self.assertEqual(
            split_params.page, 2,
        )
