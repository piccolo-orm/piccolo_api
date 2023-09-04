from unittest import TestCase

from piccolo.apps.user.tables import BaseUser
from starlette.routing import Route, Router
from starlette.testclient import TestClient

from piccolo_api.token_auth.endpoints import token_login
from piccolo_api.token_auth.tables import TokenAuth

APP = Router([Route("/", token_login())])


###############################################################################


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

        token = TokenAuth.create_token_sync(user_id=user.id)

        client = TestClient(APP)
        response = client.post("/", json=self.credentials)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token"], token)
