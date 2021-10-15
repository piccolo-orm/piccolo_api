from __future__ import annotations

import typing as t
import uuid
from collections.abc import Sequence

from starlette.datastructures import URL
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    Request,
    RequestResponseEndpoint,
)
from starlette.responses import Response
from starlette.types import ASGIApp

SAFE_HTTP_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")
ONE_YEAR = 31536000  # 365 * 24 * 60 * 60
DEFAULT_COOKIE_NAME = "csrftoken"
DEFAULT_HEADER_NAME = "X-CSRFToken"


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    For GET requests, set a random token as a cookie. For unsafe HTTP methods,
    require a HTTP header to match the cookie value, otherwise the request
    is rejected.

    This uses the Double Submit Cookie style of CSRF prevention. For more
    information:

    https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie
    https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#use-of-custom-request-headers

    By default, the CSRF token needs to be added to the request header. By
    setting `allow_form_param` to True, it will also work if added as a form
    parameter.

    """

    @staticmethod
    def get_new_token() -> str:
        return str(uuid.uuid4())

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: t.Sequence[str] = [],
        cookie_name=DEFAULT_COOKIE_NAME,
        header_name=DEFAULT_HEADER_NAME,
        max_age=ONE_YEAR,
        allow_header_param=True,
        allow_form_param=False,
        **kwargs,
    ):
        """
        :param app:
            The ASGI app you want to wrap.
        :allowed_hosts:
            If using this middleware with HTTPS, you need to set this value,
            for example ['example.com'].
        :cookie_name:
            You can specify a custom name for the cookie. There should be no
            need to change it, unless in the rare situation where the name
            clashes with another cookie.
        :header_name:
            You can tell the middleware to look for the CSRF token in a
            different HTTP header.
        :max_age:
            The max age of the cookie.
        :allow_header_param:
            Whether to look for the CSRF token in the HTTP headers.
        :allow_form_param:
            Whether to look for the CSRF token in a form field with the same
            name as the cookie. By default, it's not enabled.

        """
        if not isinstance(allowed_hosts, Sequence):
            raise ValueError(
                "allowed_hosts must be a sequence (list or tuple)"
            )

        self.allowed_hosts = allowed_hosts
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.max_age = max_age
        self.allow_header_param = allow_header_param
        self.allow_form_param = allow_form_param
        super().__init__(app, **kwargs)

    def is_valid_referer(self, request: Request) -> bool:
        header: str = (
            request.headers.get("origin")
            or request.headers.get("referer")
            or ""
        )

        url = URL(header)
        hostname = url.hostname
        is_valid = hostname in self.allowed_hosts if hostname else False
        return is_valid

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        if request.method in SAFE_HTTP_METHODS:
            token = request.cookies.get(self.cookie_name, None)
            token_required = token is None

            if token_required:
                token = self.get_new_token()

            request.scope.update(
                {
                    "csrftoken": token,
                    "csrf_cookie_name": self.cookie_name,
                }
            )
            response = await call_next(request)

            if token_required and token:
                response.set_cookie(
                    self.cookie_name,
                    token,
                    max_age=self.max_age,
                )
            return response
        else:
            cookie_token = request.cookies.get(self.cookie_name)
            if not cookie_token:
                return Response("No CSRF cookie found", status_code=403)

            if self.allow_header_param:
                header_token = request.headers.get(self.header_name, None)
            else:
                header_token = None

            if self.allow_form_param:
                form_data = await request.form()
                form_token = form_data.get(self.cookie_name, None)
                request.scope.update({"form": form_data})
            else:
                form_token = None

            if not header_token and not form_token:
                return Response(
                    "The CSRF token wasn't found in the form data or header.",
                    status_code=403,
                )

            if header_token and (cookie_token != header_token):
                return Response(
                    "The CSRF token in the header doesn't match the cookie.",
                    status_code=403,
                )

            if form_token and (cookie_token != form_token):
                return Response(
                    "The CSRF token in the form doesn't match the cookie.",
                    status_code=403,
                )

            # Provides defence in depth:
            if request.base_url.is_secure:
                # According to this paper, the referer header is present in
                # the vast majority of HTTPS requests, but not HTTP requests,
                # so only check it for HTTPS.
                # https://seclab.stanford.edu/websec/csrf/csrf.pdf
                if not self.is_valid_referer(request):
                    return Response(
                        "Referer or origin is incorrect", status_code=403
                    )

            request.scope.update(
                {
                    "csrftoken": cookie_token,
                    "csrf_cookie_name": self.cookie_name,
                }
            )

            return await call_next(request)
