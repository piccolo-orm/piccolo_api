import os
from unittest import TestCase

from piccolo.extensions.user import BaseUser
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


SQLITE_PATH = os.path.join(os.path.dirname(__file__), "./session.sqlite")
DB = SQLiteEngine(path=SQLITE_PATH)


class Sessions(SessionsBase, db=DB):
    pass


class User(BaseUser, db=DB):
    pass


def clear_database():
    if os.path.exists(SQLITE_PATH):
        os.unlink(SQLITE_PATH)


###############################################################################


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
        Route(
            "/login/",
            session_login(auth_table=User, session_table=Sessions),
            name="login",
        ),
        Route(
            "/logout/", session_logout(session_table=Sessions), name="login"
        ),
        Mount(
            "/secret",
            AuthenticationMiddleware(
                ProtectedEndpoint,
                SessionsAuthBackend(auth_table=User, session_table=Sessions),
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
        clear_database()
        Sessions.create().run_sync()
        User.create().run_sync()

    def tearDown(self):
        clear_database()

    def test_create_session(self):
        Sessions.create_session_sync(user_id=1)

    def test_login_failure(self):
        client = TestClient(APP)
        response = client.post("/login/", json=self.wrong_credentials)
        self.assertTrue(response.status_code == 401)
        self.assertTrue(response.cookies.values() == [])

    def test_login_success(self):
        client = TestClient(APP)
        User(**self.credentials).save().run_sync()
        response = client.post("/login/", json=self.credentials)
        self.assertTrue(response.status_code == 303)
        self.assertTrue("id" in response.cookies.keys())
