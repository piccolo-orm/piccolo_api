# Note - most tests for the `register` endpoint are in `test_session.py`

from unittest import TestCase

from starlette.routing import Route, Router
from starlette.testclient import TestClient

from piccolo_api.register.endpoints import register


class TestRegister(TestCase):
    def test_read_only(self):
        app = Router(routes=[Route("/", register(read_only=True))])
        client = TestClient(app)
        response = client.post("/")
        self.assertTrue(response.status_code, 405)
        self.assertTrue(response.content, "Running in read only mode.")
