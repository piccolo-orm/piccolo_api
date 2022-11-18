from unittest import TestCase

from starlette.testclient import TestClient

from piccolo_api.csp.middleware import CSPConfig, CSPMiddleware


async def app(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/plain"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"Hello, world!",
        }
    )


class TestCSPMiddleware(TestCase):
    def test_headers(self):
        wrapped_app = CSPMiddleware(app)

        client = TestClient(wrapped_app)
        response = client.request("GET", "/")

        header_names = response.headers.keys()

        # Make sure the headers got added:
        self.assertIn("content-security-policy", header_names)

        # Make sure the original headers are still intact:
        self.assertIn("content-type", header_names)

    def test_report_uri(self):
        wrapped_app = CSPMiddleware(
            app, config=CSPConfig(report_uri=b"foo.com")
        )

        client = TestClient(wrapped_app)
        response = client.request("GET", "/")

        header = response.headers["content-security-policy"]
        self.assertIn("report-uri", header)
