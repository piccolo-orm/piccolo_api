import typing as t

from piccolo.apps.user.tables import BaseUser

from piccolo_api.mfa.authenticator.tables import AuthenticatorSecret
from piccolo_api.mfa.authenticator.utils import get_b64encoded_qr_image
from piccolo_api.mfa.provider import MFAProvider


class AuthenticatorProvider(MFAProvider):

    def __init__(
        self,
        db_encryption_key: str,
        recovery_code_count: int = 8,
        secret_table: t.Type[AuthenticatorSecret] = AuthenticatorSecret,
        issuer_name: str = "Piccolo-MFA",
    ):
        """
        :param db_encryption_key:
            The shared secrets are encrypted in the database - pass in a random
            string which is used for encrypting them.
        :param recovery_code_count:
            How many recovery codes should be generated.
        :param seed_table:
            By default, just use the out of the box ``AuthenticatorSecret``
            table - you can specify a subclass instead if you want to override
            certain functionality.
        :param issuer_name:
            This is how it will be identified in the user's authenticator app.

        """
        super().__init__(token_name="authenticator_token")

        self.db_encryption_key = db_encryption_key
        self.recovery_code_count = recovery_code_count
        self.secret_table = secret_table
        self.issuer_name = issuer_name

    async def authenticate_user(self, user: BaseUser, code: str) -> bool:
        """
        The code could be a TOTP code, or a recovery code.
        """
        return await self.secret_table.authenticate(
            user_id=user.id,
            code=code,
            db_encryption_key=self.db_encryption_key,
        )

    async def is_user_enrolled(self, user: BaseUser) -> bool:
        return await self.secret_table.is_user_enrolled(user_id=user.id)

    async def send_code(self, *args, **kwargs):
        """
        Deliberately blank - the user already has the code on their phone.
        """
        pass

    ###########################################################################
    # Registration

    async def _generate_qrcode_image(
        self, secret: AuthenticatorSecret, email: str
    ):
        uri = secret.get_authentication_setup_uri(
            email=email,
            db_encryption_key=self.db_encryption_key,
            issuer_name=self.issuer_name,
        )

        return get_b64encoded_qr_image(data=uri)

    async def get_registration_html(self, user: BaseUser) -> str:
        """
        When a user wants to register for MFA, this HTML is shown containing
        instructions.
        """
        secret, recovery_codes = await self.secret_table.create_new(
            user_id=user.id,
            db_encryption_key=self.db_encryption_key,
            recovery_code_count=self.recovery_code_count,
        )

        qrcode_image = await self._generate_qrcode_image(
            secret=secret, email=user.email
        )

        recovery_codes_str = "\n".join(recovery_codes)

        return f"""
            <p>Use an authenticator app like Google Authenticator to scan this QR code:</p>
            <img src="data:image/png;base64,{qrcode_image}" />
            <p>Copy these recovery codes and keep them safe:</p>
            <textarea type="text">{recovery_codes_str}</textarea>
            """  # noqa: E501

    async def get_registration_json(self, user: BaseUser) -> dict:
        """
        When a user wants to register for MFA, the client can request a JSON
        response, rather than HTML, if they want to render the UI themselves.
        """
        secret, recovery_codes = await self.secret_table.create_new(
            user_id=user.id,
            db_encryption_key=self.db_encryption_key,
        )

        qrcode_image = await self._generate_qrcode_image(
            secret=secret, email=user.email
        )

        return {"qrcode_image": qrcode_image, "recovery_codes": recovery_codes}
