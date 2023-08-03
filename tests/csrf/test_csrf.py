from unittest import TestCase

from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.testclient import TestClient

from piccolo_api.csrf.middleware import (
    DEFAULT_COOKIE_NAME,
    DEFAULT_HEADER_NAME,
    CSRFMiddleware,
)


async def app(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


WRAPPED_APP = ExceptionMiddleware(CSRFMiddleware(app, allow_form_param=True))
HOST_RESTRICTED_APP = ExceptionMiddleware(
    CSRFMiddleware(app, allowed_hosts=["foo.com"], allow_form_param=True)
)


class TestCSRFMiddleware(TestCase):
    csrf_token = CSRFMiddleware.get_new_token()
    incorrect_csrf_token = "abc123"

    def test_get_request(self):
        """
        Make sure a cookie was set.
        """
        client = TestClient(WRAPPED_APP)
        response = client.get("/")

        self.assertIsNot(response.cookies.get("csrftoken"), None)

    def test_missing_token_rejected(self):
        """
        Make sure a post request without a CSRF token is rejected.
        """
        client = TestClient(WRAPPED_APP)
        response = client.post("/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b"No CSRF cookie found")

    def test_header_token_accepted(self):
        """
        Make sure a post containing a CSRF cookie and matching header token are
        accepted.
        """
        client = TestClient(WRAPPED_APP)

        response = client.post(
            "/",
            cookies={DEFAULT_COOKIE_NAME: self.csrf_token},
            headers={DEFAULT_HEADER_NAME: self.csrf_token},
        )
        self.assertEqual(response.status_code, 200)

    def test_form_token_accepted(self):
        """
        Make sure a post containing a CSRF cookie and matching form token are
        accepted.
        """
        client = TestClient(WRAPPED_APP)

        response = client.post(
            "/",
            cookies={DEFAULT_COOKIE_NAME: self.csrf_token},
            data={DEFAULT_COOKIE_NAME: self.csrf_token},
        )
        self.assertEqual(response.status_code, 200)

    def test_token_mismatch_rejected(self):
        """
        Make sure that just including a header or cookie doesn't somehow work.
        """
        client = TestClient(WRAPPED_APP)

        kwargs = [
            # Incorrect header, correct cookie
            {
                "cookies": {DEFAULT_COOKIE_NAME: self.csrf_token},
                "headers": {DEFAULT_HEADER_NAME: self.incorrect_csrf_token},
            },
            # Incorrect cookie, correct header token
            {
                "cookies": {DEFAULT_COOKIE_NAME: self.incorrect_csrf_token},
                "headers": {DEFAULT_HEADER_NAME: self.csrf_token},
            },
            # Correct cookie, missing header
            {
                "cookies": {DEFAULT_COOKIE_NAME: self.csrf_token},
                "headers": {},
            },
            # Missing cookie, correct header
            {
                "cookies": {},
                "headers": {DEFAULT_HEADER_NAME: self.incorrect_csrf_token},
            },
        ]

        for _kwargs in kwargs:
            response = client.post("/", **_kwargs)
            self.assertEqual(response.status_code, 403)

    def test_referer_accepted(self):
        """
        Make sure that a correct referer or origin header is allowed.
        """
        cookies = {DEFAULT_COOKIE_NAME: self.csrf_token}
        base_headers = {DEFAULT_HEADER_NAME: self.csrf_token}

        client = TestClient(HOST_RESTRICTED_APP)
        valid_domain = "https://foo.com"

        kwargs = [
            {"referer": valid_domain},
            {"referer": f"{valid_domain}/bar/"},
            {"origin": valid_domain},
            {"origin": valid_domain, "referer": valid_domain},
        ]

        for _kwargs in kwargs:
            response = client.post(
                valid_domain,
                cookies=cookies,
                headers=dict(base_headers, **_kwargs),
            )
            self.assertEqual(response.status_code, 200)

    def test_referer_rejected(self):
        """
        Make sure that an incorrect or missing referer / origin header isn't
        allowed.
        """
        cookies = {DEFAULT_COOKIE_NAME: self.csrf_token}
        base_headers = {DEFAULT_HEADER_NAME: self.csrf_token}

        client = TestClient(HOST_RESTRICTED_APP)
        invalid_domain = "https://bar.com"

        kwargs = [{"referer": invalid_domain}, {"origin": invalid_domain}, {}]

        for _kwargs in kwargs:
            response = client.post(
                "https://foo.com",
                cookies=cookies,
                headers=dict(base_headers, **_kwargs),
            )
            self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    # For manual testing:
    # python -m tests.csrf.test_csrf
    import uvicorn

    uvicorn.run(WRAPPED_APP, port=8081)
