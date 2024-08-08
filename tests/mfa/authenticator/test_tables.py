import datetime
from unittest import TestCase

from piccolo.apps.user.tables import BaseUser
from piccolo.testing.test_case import AsyncTableTest

from piccolo_api.mfa.authenticator.tables import AuthenticatorSeed


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


class TestCreateNew(AsyncTableTest):

    tables = [AuthenticatorSeed, BaseUser]

    async def test_create_new(self):
        user = await BaseUser.create_user(
            username="test", password="test123456"
        )

        seed = await AuthenticatorSeed.create_new(user_id=user.id)

        self.assertEqual(seed.id, user.id)
        self.assertIsNotNone(seed.secret)
        self.assertIsInstance(seed.created_at, datetime.datetime)
        self.assertIsNone(seed.last_used_at)
        self.assertIsNone(seed.revoked_at)
        self.assertIsNone(seed.last_used_code)
