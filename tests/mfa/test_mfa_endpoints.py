from piccolo.testing.test_case import AsyncTableTest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from piccolo_api.mfa.authenticator.provider import AuthenticatorProvider
from piccolo_api.mfa.authenticator.tables import AuthenticatorSecret
from piccolo_api.mfa.endpoints import mfa_register_endpoint


class TestMFARegisterEndpoint(AsyncTableTest):

    tables = [AuthenticatorSecret]

    async def test_register(self):
        # Rather than setting all of this up ... what if I use the example app?
        app = Starlette(
            routes=[
                Route(
                    path="/register/",
                    endpoint=mfa_register_endpoint(
                        provider=AuthenticatorProvider()
                    ),
                )
            ]
        )

        client = TestClient(app=app)

        client.get("/register/")
