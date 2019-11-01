import random

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
    Request,
)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    For GET requests, set a random token as a cookie. For unsafe HTTP methods,
    require a HTTP header to match the cookie value, otherwise the request
    is rejected.

    This uses the Double Submit Cookie style of CSRF prevention. For more
    information:

    https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        if request.method == "GET":
            response = await call_next()
            response.set_cookie("csrftoken", random.random)
            pass
        else:
            # TODO - verify header matches cookie value.
            pass

        await self.asgi(scope, receive, send)
