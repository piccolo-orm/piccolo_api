# Note - most tests for the `change_password` endpoint are in `test_session.py`

from unittest import TestCase

from starlette.routing import Route, Router
from starlette.testclient import TestClient

from piccolo_api.change_password.endpoints import change_password


class TestChangePassword(TestCase):
    def test_change_password(self):
        app = Router(routes=[Route("/", change_password(read_only=True))])
        client = TestClient(app)
        response = client.post("/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.content, b"Running in read only mode")
