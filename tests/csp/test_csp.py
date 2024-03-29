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
        """
        Make sure the headers are added.
        """
        wrapped_app = CSPMiddleware(app)

        client = TestClient(wrapped_app)
        response = client.request("GET", "/")

        # Make sure the headers got added:
        self.assertEqual(
            response.headers["content-security-policy"],
            "default-src: 'self'",
        )

        # Make sure the original headers are still intact:
        self.assertEqual(response.headers["content-type"], "text/plain")

    def test_default_src(self):
        """
        Make sure the `default-src` value can be set.
        """
        wrapped_app = CSPMiddleware(app, config=CSPConfig(default_src="none"))

        client = TestClient(wrapped_app)
        response = client.request("GET", "/")

        self.assertEqual(
            response.headers.get("content-security-policy"),
            "default-src: 'none'",
        )

    def test_report_uri(self):
        wrapped_app = CSPMiddleware(
            app, config=CSPConfig(report_uri=b"foo.com")
        )

        client = TestClient(wrapped_app)
        response = client.request("GET", "/")

        self.assertEqual(
            response.headers["content-security-policy"],
            "default-src: 'self'; report-uri foo.com",
        )
