from piccolo.apps.user.tables import BaseUser
from piccolo.testing.test_case import AsyncTableTest
from starlette.testclient import TestClient

from example_projects.mfa_demo.app import app
from piccolo_api.mfa.authenticator.tables import AuthenticatorSecret
from piccolo_api.session_auth.tables import SessionsBase


class TestMFARegisterEndpoint(AsyncTableTest):

    tables = [AuthenticatorSecret, BaseUser, SessionsBase]
    username = "alice"
    password = "test123"

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()

        self.user = await BaseUser.create_user(
            username=self.username, password=self.password, active=True
        )

    async def test_register(self):
        client = TestClient(app=app)

        # Get a CSRF cookie
        response = client.get("/login/")
        csrf_token = response.cookies["csrftoken"]
        self.assertEqual(response.status_code, 200)

        # Login
        response = client.post(
            "/login/",
            json={"username": self.username, "password": self.password},
            headers={"X-CSRFToken": csrf_token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("id", client.cookies)

        # Register for MFA - JSON
        response = client.post(
            "/private/mfa-register/",
            json={
                "action": "register",
                "format": "json",
                "password": self.password,
            },
            headers={"X-CSRFToken": csrf_token},
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("qrcode_image", data)
        self.assertIn("recovery_codes", data)

        # Register for MFA - HTML
        response = client.post(
            "/private/mfa-register/",
            data={"action": "register", "password": self.password},
            headers={"X-CSRFToken": csrf_token},
        )

        # TODO - change this, as we can't register twice.
        # self.assertEqual(response.status_code, 200)
        # html = response.content
        # self.assertIn(b"Authenticator Setup", html)
