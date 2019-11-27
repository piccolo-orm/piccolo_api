from unittest import TestCase

from piccolo_api.token_auth.middleware import TokenAuthBackend


class TestTokenAuth(TestCase):
    def test_extract_token(self):
        backend = TokenAuthBackend()
        self.assertEqual(backend.extract_token("Bearer 12345"), "12345")
