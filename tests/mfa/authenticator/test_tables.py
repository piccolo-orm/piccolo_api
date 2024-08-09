import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

from piccolo.apps.user.tables import BaseUser
from piccolo.testing.test_case import AsyncTableTest

from piccolo_api.mfa.authenticator.tables import AuthenticatorSecret


class TestGenerateSecret(TestCase):

    def test_generate_secret(self):
        """
        Make sure secrets are generated correctly.
        """
        secret_1 = AuthenticatorSecret.generate_secret()
        secret_2 = AuthenticatorSecret.generate_secret()

        self.assertIsInstance(secret_1, str)
        self.assertNotEqual(secret_1, secret_2)
        self.assertEqual(len(secret_1), 32)


class TestAuthenticate(AsyncTableTest):

    tables = [AuthenticatorSecret, BaseUser]

    @patch("piccolo_api.mfa.authenticator.tables.logger")
    async def test_replay_attack(self, logger: MagicMock):
        """
        If a token which was just used successfully is reused, it should be
        rejected, because it might be a replay attack.
        """
        user = await BaseUser.create_user(
            username="test", password="test123456"
        )

        code = "123456"

        seed = await AuthenticatorSecret.create_new(user_id=user.id)
        seed.last_used_code = code
        await seed.save()

        auth_response = await AuthenticatorSecret.authenticate(
            user_id=user.id, code=code
        )
        assert auth_response is False

        logger.warning.assert_called_with(
            "User 1 reused a token - potential replay attack."
        )


class TestCreateNew(AsyncTableTest):

    tables = [AuthenticatorSecret, BaseUser]

    async def test_create_new(self):
        user = await BaseUser.create_user(
            username="test", password="test123456"
        )

        seed = await AuthenticatorSecret.create_new(user_id=user.id)

        self.assertEqual(seed.id, user.id)
        self.assertIsNotNone(seed.secret)
        self.assertIsInstance(seed.created_at, datetime.datetime)
        self.assertIsNone(seed.last_used_at)
        self.assertIsNone(seed.revoked_at)
        self.assertIsNone(seed.last_used_code)
