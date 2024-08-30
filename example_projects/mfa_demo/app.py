import os

from jinja2 import Environment, FileSystemLoader
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Mount, Route

from piccolo_api.csrf.middleware import CSRFMiddleware
from piccolo_api.encryption.providers import FernetProvider
from piccolo_api.mfa.authenticator.provider import AuthenticatorProvider
from piccolo_api.mfa.endpoints import mfa_setup
from piccolo_api.register.endpoints import register
from piccolo_api.session_auth.endpoints import session_login, session_logout
from piccolo_api.session_auth.middleware import SessionsAuthBackend

EXAMPLE_DB_ENCRYPTION_KEY = "wqsOqyTTEsrWppZeIMS8a3l90yPUtrqT48z7FS6_U8g="


environment = Environment(
    loader=FileSystemLoader(
        os.path.join(os.path.dirname(__file__), "templates"),
    ),
    autoescape=True,
)


class HomeEndpoint(HTTPEndpoint):
    async def get(self, request):
        home_template = environment.get_template("home.html")

        return HTMLResponse(content=home_template.render())


class PrivateEndpoint(HTTPEndpoint):
    async def get(self, request):
        return HTMLResponse(
            content=(
                "<style>body{font-family: sans-serif;}</style>"
                "<h1>Private page</h1>"
            )
        )


def on_auth_error(request: Request, exc: Exception):
    return RedirectResponse("/login/")


private_app = Starlette(
    routes=[
        Route("/", PrivateEndpoint),
        Route("/logout/", session_logout(redirect_to="/")),
        Route(
            "/mfa-setup/",
            mfa_setup(
                provider=AuthenticatorProvider(
                    encryption_provider=FernetProvider(
                        encryption_key=EXAMPLE_DB_ENCRYPTION_KEY
                    )
                )
            ),
        ),
    ],
    middleware=[
        Middleware(
            AuthenticationMiddleware,
            on_error=on_auth_error,
            backend=SessionsAuthBackend(admin_only=False),
        ),
    ],
    debug=True,
)


app = Starlette(
    routes=[
        Route("/", HomeEndpoint),
        Route(
            "/login/",
            session_login(
                mfa_providers=[
                    AuthenticatorProvider(
                        encryption_provider=FernetProvider(
                            encryption_key=EXAMPLE_DB_ENCRYPTION_KEY
                        )
                    )
                ]
            ),
        ),
        Route(
            "/register/",
            register(redirect_to="/login/", user_defaults={"active": True}),
        ),
        Mount("/private/", private_app),
    ],
    middleware=[
        Middleware(CSRFMiddleware, allow_form_param=True),
    ],
)
