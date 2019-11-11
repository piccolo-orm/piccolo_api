import uuid

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
    Request,
)
from starlette.exceptions import HTTPException


SAFE_HTTP_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")


# TODO - might merge it in with session auth ...
# Same Site cookies for the session isn't something I can do here ...
class CSRFMiddleware(BaseHTTPMiddleware):
    """
    For GET requests, set a random token as a cookie. For unsafe HTTP methods,
    require a HTTP header to match the cookie value, otherwise the request
    is rejected.

    This uses the Double Submit Cookie style of CSRF prevention. For more
    information:

    https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie
    https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#use-of-custom-request-headers

    For a good explanation on how SPAs mitigate CSRF:

    https://angular.io/guide/security#xsrf
    """

    cookie_name = "csrftoken"
    header_name = "X-CSRFToken"

    def get_new_token(self) -> str:
        return str(uuid.uuid4())

    def check_referrer(self, request: Request):
        pass

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        if request.method in SAFE_HTTP_METHODS:
            response = await call_next(request)
            if not request.cookies.get(self.cookie_name):
                response.set_cookie(self.cookie_name, self.get_new_token())
        else:
            cookie_token = request.cookies.get(self.cookie_name)
            if not cookie_token:
                raise HTTPException(403, "No CSRF cookie found")

            header_token = request.headers.get(self.header_name)

            if cookie_token != header_token:
                raise HTTPException(403, "CSRF tokens don't match")

            # Check if HTTPS - if so, check referrer

            await call_next(request)
