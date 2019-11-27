from unittest import TestCase

from piccolo.extensions.user.tables import BaseUser
from piccolo.engine import engine_finder, SQLiteEngine
from piccolo_api.token_auth.endpoints import TokenAuthLoginEndpoint
from piccolo_api.token_auth.tables import TokenAuth

from starlette.routing import Router, Route
from starlette.testclient import TestClient


APP = Router([Route("/", TokenAuthLoginEndpoint)])
ENGINE: SQLiteEngine = engine_finder()


###############################################################################


class TestLoginEndpoint(TestCase):

    credentials = {"username": "Bob", "password": "bob123"}

    def setUp(self):
        ENGINE.remove_db_file()
        BaseUser.create_table().run_sync()
        TokenAuth.create_table().run_sync()

    def tearDown(self):
        ENGINE.remove_db_file()

    def test_login_success(self):
        user = BaseUser(**self.credentials)
        user.save().run_sync()

        token = TokenAuth.create_token_sync(user_id=user.id)

        client = TestClient(APP)
        response = client.post("/", json=self.credentials)

        self.assertTrue(response.status_code == 200)
        self.assertTrue(response.json()["token"] == token)
