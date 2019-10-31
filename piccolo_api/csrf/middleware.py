from starlette.types import Scope, Receive, Send, ASGIApp


class CSRFMiddleware():
    """
    For GET requests, set a random token as a cookie. For unsafe HTTP methods,
    require a HTTP header to match the cookie value, otherwise the request
    is rejected.

    This uses the Double Submit Cookie style of CSRF prevention. For more
    information:

    https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie
    """

    def __init__(
        self,
        asgi: ASGIApp,
    ) -> None:
        self.asgi = asgi

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """
        Add the user_id to the scope if a JWT token is available, and the user
        is recognised, otherwise raise a 403 HTTP error.
        """
        if scope['method'] == 'GET':
            # TODO - set cookies
            pass
        else:
            # TODO - verify header matches cookie value.
            pass

        await self.asgi(scope, receive, send)
