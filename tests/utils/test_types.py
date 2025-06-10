import sys
from typing import Optional, Union
from unittest import TestCase

import pytest

from piccolo_api.utils.types import get_type


class TestGetType(TestCase):

    def test_get_type(self):
        """
        If we pass in an optional type, it should return the non-optional type.
        """
        # Should return the underlying type, as they're all optional:
        self.assertIs(get_type(Optional[str]), str)
        self.assertEqual(get_type(Optional[list[str]]), list[str])
        self.assertIs(get_type(Union[str, None]), str)

        # Should be returned as is, because it's not optional:
        self.assertEqual(get_type(list[str]), list[str])

    @pytest.mark.skipif(
        sys.version_info < (3, 10), reason="Union syntax not available"
    )
    def test_new_union_syntax(self):
        """
        Make sure it works with the new syntax added in Python 3.10.
        """
        self.assertIs(get_type(str | None), str)  # type: ignore
        self.assertIs(get_type(None | str), str)  # type: ignore
