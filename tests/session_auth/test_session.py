from unittest import TestCase

from piccolo.extensions.user.tables import BaseUser
from piccolo.engine import engine_finder
from piccolo.engine.sqlite import SQLiteEngine
from starlette.authentication import requires
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import ExceptionMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route, Router
from starlette.testclient import TestClient

from piccolo_api.session_auth.tables import SessionsBase
from piccolo_api.session_auth.endpoints import session_login, session_logout
from piccolo_api.session_auth.middleware import SessionsAuthBackend


###############################################################################

ENGINE: SQLiteEngine = engine_finder()


class HomeEndpoint(HTTPEndpoint):
    def get(self, request):
        return PlainTextResponse("hello world")


class ProtectedEndpoint(HTTPEndpoint):
    @requires("authenticated", redirect="login")
    def get(self, request):
        return PlainTextResponse("top secret")


ROUTER = Router(
    routes=[
        Route("/", HomeEndpoint, name="home"),
        Route("/login/", session_login(), name="login",),
        Route("/logout/", session_logout(), name="login"),
        Mount(
            "/secret",
            AuthenticationMiddleware(
                ProtectedEndpoint, SessionsAuthBackend(),
            ),
        ),
    ]
)
APP = ExceptionMiddleware(ROUTER)


###############################################################################


class TestSessions(TestCase):

    credentials = {"username": "Bob", "password": "bob123"}
    wrong_credentials = {"username": "Bob", "password": "bob12345"}

    def setUp(self):
        ENGINE.remove_db_file()
        SessionsBase.create_table().run_sync()
        BaseUser.create_table().run_sync()

    def tearDown(self):
        ENGINE.remove_db_file()

    def test_create_session(self):
        SessionsBase.create_session_sync(user_id=1)

    def test_login_failure(self):
        client = TestClient(APP)
        response = client.post("/login/", json=self.wrong_credentials)
        self.assertTrue(response.status_code == 401)
        self.assertTrue(response.cookies.values() == [])

    def test_login_success(self):
        client = TestClient(APP)
        BaseUser(**self.credentials).save().run_sync()
        response = client.post("/login/", json=self.credentials)
        self.assertTrue(response.status_code == 303)
        self.assertTrue("id" in response.cookies.keys())
