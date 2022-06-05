from unittest import TestCase

from starlette.routing import Route, Router
from starlette.testclient import TestClient

from piccolo_api.register.endpoints import register
from piccolo_api.session_auth.endpoints import session_login, session_logout
from piccolo_api.shared.auth.styles import Styles


class TestStyles(TestCase):
    def test_styles(self):
        """
        Make sure the custom styles are shown in the HTML output.
        """
        custom_styles = Styles(background_color="black")
        app = Router(
            routes=[
                Route(
                    "/login/",
                    session_login(styles=custom_styles),
                ),
                Route(
                    "/logout/",
                    session_logout(styles=custom_styles),
                ),
                Route(
                    "/register/",
                    register(styles=custom_styles),
                ),
            ]
        )
        client = TestClient(app)

        for url in ("/login/", "/logout/", "/register/"):
            response = client.get(url)
            self.assertTrue(b"--background_color: black;" in response.content)
