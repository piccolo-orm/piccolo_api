from unittest import TestCase

from piccolo.utils.sync import run_sync

from piccolo_api.shared.auth.captcha import (
    HCAPTCHA_TEST_CREDENTIALS,
    RECAPTCHA_V2_TEST_CREDENTIALS,
    hcaptcha,
    recaptcha_v2,
)


class TestHcaptcha(TestCase):
    def test_validator(self):
        """
        Test calling the hCaptcha API with correct and incorrect tokens.
        """
        captcha = hcaptcha(
            site_key=HCAPTCHA_TEST_CREDENTIALS.site_key,
            secret_key=HCAPTCHA_TEST_CREDENTIALS.secret_key,
        )

        # Test correct token
        response = run_sync(
            captcha.validate(token=HCAPTCHA_TEST_CREDENTIALS.token)
        )
        self.assertTrue(response is None)

        # Test incorrect token
        incorrect_token = "10000000-aaaa-bbbb-cccc-100000000001"
        response = run_sync(captcha.validate(token=incorrect_token))
        self.assertTrue(response == "CAPTCHA failed.")


class TestRecaptchaV2(TestCase):
    def test_validator(self):
        """
        Test calling the reCAPTCHA API.
        """
        captcha = recaptcha_v2(
            site_key=RECAPTCHA_V2_TEST_CREDENTIALS.site_key,
            secret_key=RECAPTCHA_V2_TEST_CREDENTIALS.secret_key,
        )

        # Any token works when we use the test site key and secret key.
        response = run_sync(
            captcha.validate(token=RECAPTCHA_V2_TEST_CREDENTIALS.token)
        )
        self.assertTrue(response is None)
