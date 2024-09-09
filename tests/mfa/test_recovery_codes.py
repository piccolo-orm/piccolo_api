from unittest import TestCase

from piccolo_api.mfa.recovery_codes import generate_recovery_code


class TestGenerateRecoveryCode(TestCase):

    def test_randomness(self):
        self.assertNotEqual(generate_recovery_code(), generate_recovery_code())

    def test_response_format(self):
        self.assertEqual(
            generate_recovery_code(length=10, characters=["a"]),
            "aaaaa-aaaaa",
        )

    def test_no_separator(self):
        self.assertEqual(
            generate_recovery_code(length=10, characters=["a"], separator=""),
            "aaaaaaaaaa",
        )

    def test_length(self):
        with self.assertRaises(ValueError):
            generate_recovery_code(length=6),
