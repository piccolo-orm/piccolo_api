from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import HTMLResponse
from starlette.routing import Mount, Route

from piccolo_api.change_password.endpoints import change_password
from piccolo_api.csrf.middleware import CSRFMiddleware
from piccolo_api.register.endpoints import register
from piccolo_api.session_auth.endpoints import session_login
from piccolo_api.session_auth.middleware import SessionsAuthBackend


class HomeEndpoint(HTTPEndpoint):
    async def get(self, request):
        return HTMLResponse(
            content=(
                "<h1>Change Password Demo</h1>"
                '<p>First <a href="/register/">register</a></p>'  # noqa: E501
                '<p>Then <a href="/login/">login</a></p>'  # noqa: E501
                '<p>Then try <a href="/private/change-password/">changing your password</a></p>'  # noqa: E501
            )
        )


private_app = Starlette(
    routes=[
        Route("/change-password/", change_password()),
    ],
    middleware=[
        Middleware(
            AuthenticationMiddleware,
            backend=SessionsAuthBackend(admin_only=False),
        ),
    ],
)


app = Starlette(
    routes=[
        Route("/", HomeEndpoint),
        Route("/login/", session_login()),
        Route(
            "/register/",
            register(redirect_to="/login/", user_defaults={"active": True}),
        ),
        Route("/change-password/", change_password()),
        Mount("/private/", private_app),
    ],
    middleware=[
        Middleware(CSRFMiddleware, allow_form_param=True),
    ],
)
