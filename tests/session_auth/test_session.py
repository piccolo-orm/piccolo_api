import os
from unittest import TestCase

from piccolo.apps.user.tables import BaseUser
from starlette.authentication import requires
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import ExceptionMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route, Router
from starlette.testclient import TestClient

from piccolo_api.session_auth.endpoints import session_login, session_logout
from piccolo_api.session_auth.middleware import (
    SessionsAuthBackend,
    UnauthenticatedUser,
)
from piccolo_api.session_auth.tables import SessionsBase

###############################################################################


class HomeEndpoint(HTTPEndpoint):
    def get(self, request):
        data = (
            SessionsBase.select(SessionsBase.user_id)
            .where(SessionsBase.token == request.cookies.get("id"))
            .first()
            .run_sync()
        )
        if data:
            session_user = (
                BaseUser.select(BaseUser.username)
                .where(BaseUser._meta.primary_key == data["user_id"])
                .first()
                .run_sync()
            )
            return PlainTextResponse(f"hello {session_user['username']}")
        else:
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
            session_login(),
            name="login",
        ),
        Route("/logout/", session_logout(), name="login"),
        Mount(
            "/secret/",
            AuthenticationMiddleware(
                ProtectedEndpoint,
                SessionsAuthBackend(
                    admin_only=True, superuser_only=True, active_only=True
                ),
            ),
        ),
    ]
)
APP = ExceptionMiddleware(ROUTER)


###############################################################################


class SessionTestCase(TestCase):
    credentials = {"username": "Bob", "password": "bob123"}
    wrong_credentials = {"username": "Bob", "password": "bob12345"}

    def setUp(self):
        SessionsBase.create_table().run_sync()
        BaseUser.create_table().run_sync()

    def tearDown(self):
        SessionsBase.alter().drop_table().run_sync()
        BaseUser.alter().drop_table().run_sync()


class TestSessions(SessionTestCase):
    def test_create_session(self):
        """
        Make sure sessions can be stored in the database.
        """
        SessionsBase.create_session_sync(user_id=1)
        self.assertEqual(
            SessionsBase.select("user_id").run_sync(), [{"user_id": 1}]
        )

    def test_login_wrong_credentials(self):
        """
        Make sure a user can't login using wrong credentials.
        """
        client = TestClient(APP)
        BaseUser(
            **self.credentials, active=True, admin=True, superuser=True
        ).save().run_sync()

        # Test with the wrong username and password.
        response = client.post("/login/", json=self.wrong_credentials)
        self.assertTrue(response.status_code == 401)
        self.assertTrue(response.cookies.values() == [])

        # Test with the correct username, but wrong password.
        response = client.post(
            "/login/",
            json={
                "username": self.credentials["username"],
                "password": self.wrong_credentials["password"],
            },
        )
        self.assertTrue(response.status_code == 401)
        self.assertTrue(response.cookies.values() == [])

    def test_login_success(self):
        """
        Make sure a user with the correct permissions can access the protected
        endpoint.
        """
        client = TestClient(APP)
        BaseUser(
            **self.credentials, active=True, admin=True, superuser=True
        ).save().run_sync()
        response = client.post("/login/", json=self.credentials)
        self.assertTrue(response.status_code == 303)
        self.assertTrue("id" in response.cookies.keys())

        response = client.get("/secret/")
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.content, b"top secret")

    def test_no_cookie(self):
        """
        Make sure a user with no cookie can't access the protected endpoint.
        """
        client = TestClient(APP)
        response = client.get("/secret/")
        self.assertEqual(response.content, b"No session cookie found.")
        self.assertTrue(response.status_code == 400)

    def test_wrong_cookie_value(self):
        """
        Make sure a user with a cookie, but containing an incorrect session id
        can't access the protected endpoint.
        """
        client = TestClient(APP)
        response = client.get("/secret/", cookies={"id": "abc123"})
        self.assertEqual(response.content, b"No matching session found.")
        self.assertTrue(response.status_code == 400)

    def test_inactive_user(self):
        """
        Inactive users should be rejected by the middleware, if configured
        that way.
        """
        client = TestClient(APP)
        BaseUser(
            **self.credentials, active=False, admin=True, superuser=True
        ).save().run_sync()
        response = client.post("/login/", json=self.credentials)

        # Currently the login is successful if the user is inactive - this
        # should change in the future.
        self.assertTrue(response.status_code == 303)

        # Make a request using the session - it should get rejected.
        response = client.get("/secret/")
        self.assertTrue(response.status_code == 400)
        self.assertEqual(response.content, b"Active users only")

    def test_non_superuser(self):
        """
        Non-superusers should by rejected by the middleware, if configured
        that way.
        """
        client = TestClient(APP)
        BaseUser(
            **self.credentials, active=True, admin=True, superuser=False
        ).save().run_sync()
        response = client.post("/login/", json=self.credentials)
        self.assertTrue(response.status_code == 303)

        # Make a request using the session - it should get rejected.
        response = client.get("/secret/")
        self.assertTrue(response.status_code == 400)
        self.assertEqual(response.content, b"Superusers only")

    def test_non_admin(self):
        """
        Non-admin users should be rejected by the middleware, if configured
        that way.
        """
        client = TestClient(APP)
        BaseUser(
            **self.credentials, active=True, admin=False, superuser=False
        ).save().run_sync()
        response = client.post("/login/", json=self.credentials)
        self.assertTrue(response.status_code == 303)

        # Make a request using the session - it should get rejected.
        response = client.get("/secret/")
        self.assertTrue(response.status_code == 400)
        self.assertEqual(response.content, b"Admin users only")

    def test_default_login_template(self):
        """
        Make sure the default login template works.
        """
        app = session_login()
        client = TestClient(app)
        response = client.get("/")
        self.assertTrue(b"<h1>Login</h1>" in response.content)

    def test_simple_custom_login_template(self):
        """
        Make sure that a custom login template can be used.
        """
        template_path = os.path.join(
            os.path.dirname(__file__),
            "templates",
            "simple_login_template",
            "login.html",
        )
        app = session_login(template_path=template_path)
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(response.content, b"<p>Hello world</p>")

    def test_complex_custom_login_template(self):
        """
        Make sure that a complex custom login template can be used, which use
        Jinja features like 'extends' and 'block'.
        """
        template_path = os.path.join(
            os.path.dirname(__file__),
            "templates",
            "complex_login_template",
            "login.html",
        )
        app = session_login(template_path=template_path)
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(response.content, b"<p>Hello world</p>")

    def test_logout_success(self):
        """
        Make sure a POST request sent to `session_logout` will log out the
        user.
        """
        client = TestClient(APP)
        BaseUser(
            **self.credentials, active=True, admin=True, superuser=True
        ).save().run_sync()

        response = client.post("/login/", json=self.credentials)
        self.assertTrue(response.status_code == 303)
        self.assertTrue("id" in response.cookies.keys())

        app = session_logout()
        client = TestClient(app)

        response = client.post(
            "/logout/",
            cookies={"id": response.cookies.get("id")},
            json=self.credentials,
        )
        self.assertTrue(response.status_code == 200)
        self.assertEqual(response.content, b"Successfully logged out")

    def test_logout_get_template(self):
        """
        Make sure a GET request to `session_logout` returns a logout form.
        """
        client = TestClient(session_logout())
        response = client.get("/")
        self.assertTrue(response.status_code == 200)
        self.assertTrue(
            response.headers["content-type"] == "text/html; charset=utf-8"
        )
        self.assertTrue(b"<h1>Logout</h1>" in response.content)


class EchoEndpoint(HTTPEndpoint):
    def get(self, request):
        user = request.user
        return JSONResponse(
            {
                "is_unauthenticated_user": isinstance(
                    user, UnauthenticatedUser
                ),
                "is_authenticated": user.is_authenticated,
            }
        )


class TestAllowUnauthenticated(SessionTestCase):
    """
    Make sure that if `allow_unauthenticated=True`, then the middleware
    allows the request to continue.
    """

    def create_user_and_session(self):
        user = BaseUser(
            **self.credentials, active=True, admin=True, superuser=True
        )
        user.save().run_sync()
        SessionsBase.create_session_sync(user_id=user.id)

    def setUp(self):
        super().setUp()

        # Add a session to the database to make it more realistic.
        self.create_user_and_session()

    def test_no_cookie(self):
        """
        Make sure it works when there is no cookie with the correct name.
        """
        app = AuthenticationMiddleware(
            EchoEndpoint,
            SessionsAuthBackend(allow_unauthenticated=True),
        )
        client = TestClient(app)

        # Test it with no cookie set
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"is_unauthenticated_user": True, "is_authenticated": False},
        )

    def test_wrong_cookie_value(self):
        """
        Make sure it works when there is a cookie with the correct name, but
        an incorrect value.
        """
        app = AuthenticationMiddleware(
            EchoEndpoint,
            SessionsAuthBackend(allow_unauthenticated=True),
        )
        client = TestClient(app)

        # Test it with a cookie set, but containing an incorrect token.
        response = client.get("/", cookies={"id": "abc123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"is_unauthenticated_user": True, "is_authenticated": False},
        )
