from unittest import TestCase

from piccolo.apps.user.tables import BaseUser
from piccolo.utils.sync import run_sync
from starlette.authentication import AuthenticationError

from piccolo_api.token_auth.middleware import (
    PiccoloTokenAuthProvider,
    SecretTokenAuthProvider,
    TokenAuthBackend,
)
from piccolo_api.token_auth.tables import TokenAuth


class TestPiccoloToken(TestCase):

    credentials = {"username": "Bob", "password": "bob123"}

    def setUp(self):
        BaseUser.create_table().run_sync()
        TokenAuth.create_table().run_sync()

    def tearDown(self):
        TokenAuth.alter().drop_table().run_sync()
        BaseUser.alter().drop_table().run_sync()

    def test_invalid_token_faliure(self):
        provider = PiccoloTokenAuthProvider()

        with self.assertRaises(AuthenticationError):
            run_sync(provider.get_user("12345"))

    def test_sucess(self):
        provider = PiccoloTokenAuthProvider()

        user = BaseUser(**self.credentials)
        user.save().run_sync()

        token = TokenAuth.create_token_sync(user_id=user.id)

        queried_user = run_sync(provider.get_user(token))

        self.assertEqual(user.username, queried_user.user["username"])


class TestSecretTokenAuth(TestCase):
    def test_get_user(self):
        token = "12345"
        provider = SecretTokenAuthProvider(tokens=[token])
        user = run_sync(provider.get_user(token))

        self.assertEqual(user.username, "secret_token_user")

    def test_get_user_failure(self):
        provider = SecretTokenAuthProvider(tokens=[])

        with self.assertRaises(AuthenticationError):
            run_sync(provider.get_user("12345"))


class TestTokenAuth(TestCase):
    def test_extract_token(self):
        backend = TokenAuthBackend()
        self.assertEqual(backend.extract_token("Bearer 12345"), "12345")

    def test_extract_token_failure(self):
        backend = TokenAuthBackend()
        with self.assertRaises(AuthenticationError):
            backend.extract_token("Bearer")
