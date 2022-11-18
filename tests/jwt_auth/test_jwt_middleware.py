from unittest import TestCase

import jwt
from piccolo.apps.user.tables import BaseUser
from starlette.exceptions import HTTPException
from starlette.routing import Route, Router
from starlette.testclient import TestClient

from piccolo_api.jwt_auth.middleware import JWTMiddleware
from piccolo_api.token_auth.tables import TokenAuth

APP = Router([Route("/", lambda endpoint: endpoint)])

APP = JWTMiddleware(asgi=APP, secret="SECRET")  # type: ignore


class TestJWTMiddleware(TestCase):
    def setUp(self):
        BaseUser.create_table().run_sync()
        TokenAuth.create_table().run_sync()

    def tearDown(self):
        TokenAuth.alter().drop_table().run_sync()
        BaseUser.alter().drop_table().run_sync()

    def test_empty_token(self):
        client = TestClient(APP)

        with self.assertRaises(HTTPException):
            response = client.get("/")

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["detail"], "Token not found")

    def test_invalid_token_format(self):
        client = TestClient(APP)

        with self.assertRaises(HTTPException):
            response = client.get("/", headers={"authorization": "12345"})

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["detail"], "Token not found")

    def test_expired_token(self):
        client = TestClient(APP)

        token = jwt.encode({"user_id": 1}, "SECRET")

        with self.assertRaises(HTTPException):
            response = client.get(
                "/", headers={"authorization": f"Bearer {token}"}
            )

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["detail"], "Token has expired")

    def test_token_without_user_id(self):
        client = TestClient(APP)

        token = jwt.encode({}, "SECRET")

        with self.assertRaises(HTTPException):
            response = client.get(
                "/", headers={"authorization": f"Bearer {token}"}
            )

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.content, b"")
