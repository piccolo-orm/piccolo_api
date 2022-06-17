from piccolo.apps.user.tables import BaseUser
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import HTMLResponse
from starlette.routing import Mount, Route

from piccolo_api.register.endpoints import register
from piccolo_api.shared.auth.captcha import (
    HCAPTCHA_TEST_CREDENTIALS,
    RECAPTCHA_V2_TEST_CREDENTIALS,
    hcaptcha,
    recaptcha_v2,
)
from piccolo_api.shared.auth.styles import Styles


class HomeEndpoint(HTTPEndpoint):
    async def get(self, request):
        """
        An example endpoint which shows which users have been created.
        """
        usernames = await BaseUser.select(BaseUser.username).output(
            as_list=True
        )
        usernames_string = ", ".join(usernames) if usernames else "None"
        return HTMLResponse(
            content=(
                f"<p>Users: {usernames_string}</p>"
                '<p><a href="/register/">Register</a></p>'
                '<p><a href="/register/hcaptcha/">Register with hCaptcha</a></p>'  # noqa: E501
                '<p><a href="/register/recaptcha/">Register with reCAPTCHA</a></p>'  # noqa: E501
                '<p><a href="/register/custom-styles/">Register with custom styles</a></p>'  # noqa: E501
            )
        )


app = Starlette(
    routes=[
        Route("/", HomeEndpoint),
        # Using hcaptcha
        Mount(
            "/register/hcaptcha/",
            register(
                captcha=hcaptcha(
                    site_key=HCAPTCHA_TEST_CREDENTIALS.site_key,
                    secret_key=HCAPTCHA_TEST_CREDENTIALS.secret_key,
                ),
                redirect_to="/",
            ),
        ),
        # Using recaptcha
        Mount(
            "/register/recaptcha/",
            register(
                captcha=recaptcha_v2(
                    site_key=RECAPTCHA_V2_TEST_CREDENTIALS.site_key,
                    secret_key=RECAPTCHA_V2_TEST_CREDENTIALS.secret_key,
                ),
                redirect_to="/",
            ),
        ),
        # Custom styles
        Mount(
            "/register/custom-styles/",
            register(
                redirect_to="/",
                styles=Styles(
                    background_color="green",
                    text_color="white",
                    foreground_color="black",
                    button_color="orange",
                    button_text_color="yellow",
                    error_text_color="yellow",
                ),
            ),
        ),
        # Basic
        Mount(
            "/register/",
            register(redirect_to="/"),
        ),
    ],
)
