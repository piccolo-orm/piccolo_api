from unittest import TestCase

from piccolo.apps.user.tables import BaseUser
from starlette.exceptions import HTTPException
from starlette.routing import Route, Router
from starlette.testclient import TestClient

from piccolo_api.jwt_auth.endpoints import jwt_login
from piccolo_api.token_auth.tables import TokenAuth

APP = Router([Route("/", jwt_login(secret="SECRET"))])


class TestLoginEndpoint(TestCase):
    credentials = {"username": "Bob", "password": "bob123"}

    def setUp(self):
        BaseUser.create_table().run_sync()
        TokenAuth.create_table().run_sync()

    def tearDown(self):
        TokenAuth.alter().drop_table().run_sync()
        BaseUser.alter().drop_table().run_sync()

    def test_login_success(self):
        user = BaseUser(**self.credentials)
        user.save().run_sync()

        client = TestClient(APP)
        response = client.post("/", json=self.credentials)

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())

    def test_login_failure(self):
        user = BaseUser(**self.credentials)
        user.save().run_sync()

        client = TestClient(APP)
        with self.assertRaises(HTTPException):
            response = client.post(
                "/", json={"username": "Bob", "password": "wrong"}
            )
            self.assertEqual(response.status_code, 401)
