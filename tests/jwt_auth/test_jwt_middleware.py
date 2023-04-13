import datetime
from unittest import TestCase

import jwt
from fastapi import FastAPI
from piccolo.apps.user.tables import BaseUser
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Router
from starlette.testclient import TestClient

from piccolo_api.jwt_auth.middleware import JWTError, JWTMiddleware
from piccolo_api.token_auth.tables import TokenAuth


class EchoEndpoint(HTTPEndpoint):
    def get(self, request: Request):
        return JSONResponse(
            {
                "user_id": request.scope.get("user_id"),
                "jwt_error": request.scope.get("jwt_error"),
            }
        )


FASTAPI_APP = FastAPI(title="Test visible paths")

ECHO_APP = Router([Route("/", EchoEndpoint)])
APP = JWTMiddleware(asgi=ECHO_APP, secret="SECRET")
APP_UNAUTH = JWTMiddleware(
    asgi=ECHO_APP, secret="SECRET", allow_unauthenticated=True
)
APP_VISIBLE_PATHS = JWTMiddleware(
    asgi=FASTAPI_APP, secret="SECRET", visible_paths=["/docs"]
)


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
            self.assertEqual(
                response.json()["detail"], JWTError.token_not_found.value
            )

        # allow_unauthenticated
        client = TestClient(
            JWTMiddleware(
                asgi=ECHO_APP, secret="SECRET", allow_unauthenticated=True
            )
        )
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {"user_id": None, "jwt_error": JWTError.token_not_found.value},
        )

    def test_invalid_token_format(self):
        client = TestClient(APP)

        headers = {"authorization": "12345"}

        with self.assertRaises(HTTPException):
            response = client.get("/", headers=headers)

            self.assertEqual(response.status_code, 404)
            self.assertEqual(
                response.json()["detail"], JWTError.token_not_found.value
            )

        # allow_unauthenticated
        client = TestClient(APP_UNAUTH)
        response = client.get("/", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {"user_id": None, "jwt_error": JWTError.token_not_found.value},
        )

    def test_expired_token(self):
        client = TestClient(APP)

        token = jwt.encode(
            {
                "user_id": 1,
                "exp": datetime.datetime.now(tz=datetime.timezone.utc)
                - datetime.timedelta(minutes=5),
            },
            "SECRET",
        )

        headers = {"authorization": f"Bearer {token}"}

        with self.assertRaises(HTTPException):
            response = client.get("/", headers=headers)

            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                response.json()["detail"], JWTError.token_expired.value
            )

        # allow_unauthenticated
        client = TestClient(APP_UNAUTH)
        response = client.get("/", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {"user_id": None, "jwt_error": JWTError.token_expired.value},
        )

    def test_wrong_secret(self):
        client = TestClient(APP)

        token = jwt.encode(
            {
                "user_id": 1,
                "exp": datetime.datetime.now(tz=datetime.timezone.utc)
                + datetime.timedelta(minutes=5),
            },
            "WRONG_SECRET",
        )

        headers = {"authorization": f"Bearer {token}"}

        with self.assertRaises(HTTPException):
            response = client.get("/", headers=headers)

            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                response.json()["detail"], JWTError.token_invalid.value
            )

        # allow_unauthenticated
        client = TestClient(APP_UNAUTH)
        response = client.get("/", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {"user_id": None, "jwt_error": JWTError.token_invalid.value},
        )

    def test_missing_expiry(self):
        client = TestClient(APP)

        token = jwt.encode(
            {
                "user_id": 1,
                "exp": datetime.datetime.now(tz=datetime.timezone.utc)
                - datetime.timedelta(minutes=5),
            },
            "SECRET",
        )

        headers = {"authorization": f"Bearer {token}"}

        with self.assertRaises(HTTPException):
            response = client.get("/", headers=headers)

            self.assertEqual(response.status_code, 403)
            self.assertEqual(
                response.json()["detail"], JWTError.token_expired.value
            )

        # allow_unauthenticated
        client = TestClient(APP_UNAUTH)
        response = client.get("/", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {"user_id": None, "jwt_error": JWTError.token_expired.value},
        )

    def test_token_without_user_id(self):
        client = TestClient(APP)

        token = jwt.encode({}, "SECRET")
        headers = {"authorization": f"Bearer {token}"}

        with self.assertRaises(HTTPException):
            response = client.get("/", headers=headers)

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.content, b"")

        # allow_unauthenticated
        client = TestClient(APP_UNAUTH)
        response = client.get("/", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {"user_id": None, "jwt_error": JWTError.user_not_found.value},
        )

    def test_visible_paths(self):
        client = TestClient(FASTAPI_APP)

        response = client.get("/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"<title>Test visible paths - Swagger UI</title>",
            response.content,
        )
