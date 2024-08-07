from unittest import TestCase

from piccolo_api.mfa.authenticator.tables import AuthenticatorSeed
from piccolo.ta


class TestGenerateSecret(TestCase):

    def test_generate_secret(self):
        """
        Make sure secrets are generated correctly.
        """
        secret_1 = AuthenticatorSeed.generate_secret()
        secret_2 = AuthenticatorSeed.generate_secret()

        self.assertIsInstance(secret_1, str)
        self.assertNotEqual(secret_1, secret_2)
        self.assertEqual(len(secret_1), 32)

