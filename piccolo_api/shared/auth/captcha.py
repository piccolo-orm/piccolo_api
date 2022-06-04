import inspect
import typing as t
from dataclasses import dataclass

import httpx

Response = t.Optional[str]
Validator = t.Union[
    t.Callable[[str], Response],
    t.Callable[[str], t.Awaitable[Response]],
]


@dataclass
class Captcha:
    """
    Used to create CAPTCHAs for adding bot protection to endpoints. This is
    a generic class for implementing your own CAPTCHA. Out of the box support
    is provided for :func:`hcaptcha <hcaptcha>` and
    :func:`recaptcha_v2 <recaptcha_v2>`, so you should only need to use this
    class directly if doing something custom.

    :param form_html:
        Any HTML which needs inserting into the form to make the CAPTCHA work.
    :param validator:
        A callback (either an async or normal function), which is passed the
        CAPTCHA token, and is used to verify with the CAPTCHA provider's API
        that the token is valid. To indicate that validation has failed, return
        a string containing an error message which will be shown to the user.

    """

    form_html: str
    token_field: str
    validator: Validator

    async def validate(self, token: str) -> t.Optional[str]:
        if self.validator:
            if inspect.iscoroutinefunction(self.validator):
                return await self.validator(token)  # type: ignore
            elif inspect.isfunction(self.validator):
                return self.validator(token)

        return None


@dataclass
class TestCredentials:
    site_key: str
    secret_key: str
    token: str


# These can be used to test hCaptcha
# From here: https://docs.hcaptcha.com/#integration-testing-test-keys
HCAPTCHA_TEST_CREDENTIALS = TestCredentials(
    site_key="10000000-ffff-ffff-ffff-000000000001",
    secret_key="0x0000000000000000000000000000000000000000",
    token="10000000-aaaa-bbbb-cccc-000000000001",
)


def hcaptcha(site_key: str, secret_key: str) -> Captcha:
    """
    Can be used along with Piccolo endpoints to incorporate
    `hCaptcha <https://www.hcaptcha.com/>`_.

    :param site_key:
        Provided by hCaptcha.
    :param secret_key:
        Provided by hCaptcha.

    """

    async def validator(token: str) -> t.Optional[str]:
        if not token:
            return "Unable to find CAPTCHA token."

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://hcaptcha.com/siteverify",
                data={
                    "secret": secret_key,
                    "response": token,
                },
            )
            data = response.json()
            if not data.get("success", None) is True:
                return "CAPTCHA failed."

        return None

    return Captcha(
        form_html=f"""
        <div class="h-captcha" data-sitekey="{site_key}"></div>
        <script src="https://js.hcaptcha.com/1/api.js" async defer></script>
        """,
        token_field="h-captcha-response",
        validator=validator,
    )


# These can be used to test reCAPTCHA
# From here: https://developers.google.com/recaptcha/docs/faq#id-like-to-run-automated-tests-with-recaptcha.-what-should-i-do  # noqa: E501
RECAPTCHA_V2_TEST_CREDENTIALS = TestCredentials(
    site_key="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
    secret_key="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe",
    token="abc123",  # Any token will pass
)


def recaptcha_v2(site_key: str, secret_key: str) -> Captcha:
    """
    Can be used along with Piccolo endpoints to incorporate
    `reCAPTCHA <https://developers.google.com/recaptcha>`_.

    :param site_key:
        Provided by reCAPTCHA.
    :param secret_key:
        Provided by reCAPTCHA.

    """

    async def validator(token: str) -> t.Optional[str]:
        if not token:
            return "Unable to find CAPTCHA token."

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": secret_key,
                    "response": token,
                },
            )
            data = response.json()
            if not data.get("success", None) is True:
                return "CAPTCHA failed."

        return None

    return Captcha(
        form_html=f"""
        <div class="g-recaptcha" data-sitekey="{site_key}"></div>
        <script src="https://www.google.com/recaptcha/api.js" async defer></script>
        """,  # noqa: E501
        token_field="g-recaptcha-response",
        validator=validator,
    )
