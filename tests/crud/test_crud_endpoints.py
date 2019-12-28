from unittest import TestCase

from piccolo_api.crud.endpoints import PiccoloCRUD


class TestEndpoints(TestCase):
    def test_split_params(self):
        params = {"age__operator": "gt", "age": 25}
        split_params = PiccoloCRUD._split_params(params)
        self.assertEqual(
            split_params,
            {
                "operators": {"age": "gt"},
                "fields": {"age": 25},
                "include_readable": False,
            },
        )

        params = {"readable": "true"}
        split_params = PiccoloCRUD._split_params(params)
        self.assertEqual(
            split_params,
            {"operators": {}, "fields": {}, "include_readable": True},
        )
