import inspect
import typing as t
from dataclasses import dataclass

import httpx

Dict = t.Dict[str, t.Any]
Response = t.Optional[str]
Validator = t.Union[
    t.Callable[[Dict], Response],
    t.Callable[[Dict], t.Awaitable[Response]],
]


@dataclass
class Captcha:
    """
    Used to create CAPTCHA's for adding bot protection to endpoints.

    :param form_html:
        Any HTML which needs inserting into the form to make the CAPTCHA work.
    :param validator:
        A callback (either an async or normal function), which is passed the
        form data, and is used to verify with the CAPTCHA provider's API that
        the token is valid. To indicate that validation has failed, return a
        string containing an error message which will be shown to the user.

    """

    form_html: t.Optional[str] = None
    validator: t.Optional[Validator] = None

    async def validate(self, form_data: t.Dict[str, t.Any]) -> t.Optional[str]:
        if self.validator:
            if inspect.iscoroutinefunction(self.validator):
                return await self.validator(form_data)  # type: ignore
            elif inspect.isfunction(self.validator):
                return self.validator(form_data)

        return None


# These can be used to test hCaptcha
# From here: https://docs.hcaptcha.com/#integration-testing-test-keys
HCAPTCHA_TEST_CREDENTIALS = {
    "site_key": "10000000-ffff-ffff-ffff-000000000001",
    "secret_key": "0x0000000000000000000000000000000000000000",
}


def hcaptcha(site_key: str, secret_key: str) -> Captcha:
    """
    Can be used along with Piccolo endpoints to incorporate
    `hCaptcha <https://www.hcaptcha.com/>`_.

    :param site_key:
        Provided by hCaptcha.
    :param secret_key:
        Provided by hCaptcha.

    """

    async def validator(form_data: t.Dict[str, t.Any]) -> t.Optional[str]:
        token = form_data.get("h-captcha-response", None)
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
        validator=validator,
    )


# These can be used to test reCAPTCHA
# From here: https://developers.google.com/recaptcha/docs/faq
RECAPTCHA_TEST_CREDENTIALS = {
    "site_key": "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
    "secret_key": "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe",
}


def recaptcha_v2(site_key: str, secret_key: str) -> Captcha:
    """
    Can be used along with Piccolo endpoints to incorporate
    `reCAPTCHA <https://developers.google.com/recaptcha>`_.

    :param site_key:
        Provided by reCAPTCHA.
    :param secret_key:
        Provided by reCAPTCHA.

    """

    async def validator(form_data: t.Dict[str, t.Any]) -> t.Optional[str]:
        token = form_data.get("g-recaptcha-response", None)
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
        validator=validator,
    )
