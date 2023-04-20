from unittest import TestCase

from fastapi import FastAPI
from piccolo.apps.user.tables import BaseUser
from piccolo.utils.sync import run_sync
from starlette.authentication import AuthenticationError
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.testclient import TestClient

from piccolo_api.token_auth.middleware import (
    PiccoloTokenAuthProvider,
    SecretTokenAuthProvider,
    TokenAuthBackend,
)
from piccolo_api.token_auth.tables import TokenAuth

fastapi_app = FastAPI(title="Test excluded paths")

fastapi_app_wildcard = FastAPI()


@fastapi_app_wildcard.get("/path/")
def home_root():
    return "Root"


@fastapi_app_wildcard.get("/path/a/")
def sub_root():
    return "Sub route"


APP_EXCLUDED_PATHS = AuthenticationMiddleware(
    fastapi_app,
    backend=TokenAuthBackend(
        PiccoloTokenAuthProvider(), excluded_paths=["/docs"]
    ),
)

APP_EXCLUDED_PATHS_WILDCARD = AuthenticationMiddleware(
    fastapi_app_wildcard,
    backend=TokenAuthBackend(
        PiccoloTokenAuthProvider(),
        excluded_paths=["/path/*"],
    ),
)


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


class TestExcludedPaths(TestCase):
    def test_excluded_paths(self):
        client = TestClient(APP_EXCLUDED_PATHS)

        response = client.get("/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"<title>Test excluded paths - Swagger UI</title>",
            response.content,
        )

    def test_excluded_paths_wildcard(self):
        client = TestClient(APP_EXCLUDED_PATHS_WILDCARD)

        response = client.get("/")
        # Requires a authorization header
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content,
            b"The Authorization header is missing.",
        )

        # Is an excluded path, so doesn't need a authorization header
        response = client.get("/path/a/")
        self.assertEqual(response.status_code, 200)
