import typing as t

from piccolo.apps.user.tables import BaseUser

from piccolo_api.mfa.authenticator.tables import AuthenticatorSecret
from piccolo_api.mfa.provider import MFAProvider


class AuthenticatorProvider(MFAProvider):

    def __init__(
        self,
        secret_table: t.Type[AuthenticatorSecret] = AuthenticatorSecret,
        issuer_name: str = "Piccolo-MFA",
    ):
        """
        :param seed_table:
            By default, just use the out of the box ``AuthenticatorSecret``
            table - you can specify a subclass instead if you want to override
            certain functionality.
        :param issuer_name:
            This is how it will identified in the user's authenticator app.

        """
        self.secret_table = secret_table
        self.issuer_name = issuer_name

    async def authenticate_user(self, user: BaseUser, code: str) -> bool:
        return await self.secret_table.authenticate(user_id=user.id, code=code)

    async def is_user_enrolled(self, user: BaseUser) -> bool:
        return await self.secret_table.is_user_enrolled(user_id=user.id)

    async def send_code(self, *args, **kwargs):
        """
        Deliberately blank - the user already has the code on their phone.
        """
        pass

    async def get_registration_html(self, user: BaseUser) -> str:
        """
        When a user wants to register for MFA, this HTML is shown containing
        instructions.
        """
        return """
            <p>Use an authenticator app like Google Authenticator to scan this QR code:</p>
            """  # noqa: E501
