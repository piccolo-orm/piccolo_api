from unittest import TestCase

from fastapi import FastAPI
from piccolo_api.openapi.endpoints import swagger_ui
from starlette.testclient import TestClient


class TestSwaggerUI(TestCase):
    def test_fastapi(self):
        """
        Make sure swagger_ui can be mounted within a FastAPI app.
        """
        app = FastAPI(docs_url=None, redoc_url=None)
        app.add_route("/docs/", swagger_ui())

        client = TestClient(app)
        response = client.get("/docs/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.find(b"Piccolo Swagger UI") != -1)
