from unittest import TestCase

from piccolo.utils.sync import run_sync

from piccolo_api.shared.auth.captcha import (
    HCAPTCHA_TEST_CREDENTIALS,
    Captcha,
    hcaptcha,
)


class TestHCaptcha(TestCase):
    def test_validator(self):
        """
        With the test credentials, the CAPTCHA provider's API will always
        return success. We are just testing that the API calling logic is
        correct.
        """
        captcha: Captcha = hcaptcha(
            site_key=HCAPTCHA_TEST_CREDENTIALS.site_key,
            secret_key=HCAPTCHA_TEST_CREDENTIALS.secret_key,
        )
        response = run_sync(
            captcha.validate(token=HCAPTCHA_TEST_CREDENTIALS.token)
        )
        self.assertTrue(response is None)
