import os
import typing as t

from jinja2 import Environment, FileSystemLoader
from piccolo.apps.user.tables import BaseUser

from piccolo_api.encryption.providers import EncryptionProvider
from piccolo_api.mfa.authenticator.tables import AuthenticatorSecret
from piccolo_api.mfa.authenticator.utils import get_b64encoded_qr_image
from piccolo_api.mfa.provider import MFAProvider
from piccolo_api.shared.auth.styles import Styles

MFA_SETUP_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "templates",
    "mfa_authenticator_setup.html",
)


class AuthenticatorProvider(MFAProvider):

    def __init__(
        self,
        encryption_provider: EncryptionProvider,
        recovery_code_count: int = 8,
        secret_table: t.Type[AuthenticatorSecret] = AuthenticatorSecret,
        issuer_name: str = "Piccolo-MFA",
        register_template_path: t.Optional[str] = None,
        styles: t.Optional[Styles] = None,
        valid_window: int = 0,
    ):
        """
        Allows authentication using an authenticator app on the user's phone,
        like Google Authenticator.

        :param encryption_provider:
            The shared secrets can be encrypted in the database. We recommend
            using :class:`XChaCha20Provider <piccolo_api.encryption.providers.XChaCha20Provider>`.
            Use :class:`PlainTextProvider <piccolo_api.encryption.providers.PlainTextProvider>`
            to store the secrets as plain text.
        :param recovery_code_count:
            How many recovery codes should be generated.
        :param secret_table:
            This is the table used to store secrets. You shouldn't have to
            override this, unless you subclassed the default
            ``AuthenticatorSecret`` table for some reason.
        :param issuer_name:
            This is how it will be identified in the user's authenticator app.
        :param register_template_path:
            You can override the HTML template if you want. Try using the
            ``styles`` param instead though if possible if you just want basic
            visual changes.
        :param styles:
            Modify the appearance of the HTML template using CSS.
        :param valid_window:
            Extends the validity to this many counter ticks before and after
            the current one. Increasing it is more convenient for users, but
            is less secure.

        """  # noqa: E501
        super().__init__(
            name="Authenticator App",
        )

        self.encryption_provider = encryption_provider
        self.recovery_code_count = recovery_code_count
        self.secret_table = secret_table
        self.issuer_name = issuer_name
        self.styles = styles or Styles()
        self.valid_window = valid_window

        # Load the Jinja Template
        register_template_path = (
            register_template_path or MFA_SETUP_TEMPLATE_PATH
        )
        directory, filename = os.path.split(register_template_path)
        environment = Environment(
            loader=FileSystemLoader(directory), autoescape=True
        )
        self.register_template = environment.get_template(filename)

    async def authenticate_user(self, user: BaseUser, code: str) -> bool:
        """
        The code could be a TOTP code, or a recovery code.
        """
        return await self.secret_table.authenticate(
            user_id=user.id,
            code=code,
            encryption_provider=self.encryption_provider,
            valid_window=self.valid_window,
        )

    async def is_user_enrolled(self, user: BaseUser) -> bool:
        return await self.secret_table.is_user_enrolled(user_id=user.id)

    async def send_code(self, *args, **kwargs) -> bool:
        """
        Deliberately blank - the user already has the code on their phone.
        """
        return False

    ###########################################################################
    # Registration

    async def _generate_qrcode_image(
        self, secret: AuthenticatorSecret, email: str
    ):
        uri = secret.get_authentication_setup_uri(
            email=email,
            encryption_provider=self.encryption_provider,
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
            encryption_provider=self.encryption_provider,
            recovery_code_count=self.recovery_code_count,
        )

        qrcode_image = await self._generate_qrcode_image(
            secret=secret, email=user.email
        )

        return self.register_template.render(
            qrcode_image=qrcode_image,
            recovery_codes=recovery_codes,
            recovery_codes_str="\n".join(recovery_codes),
            styles=self.styles,
        )

    async def get_registration_json(self, user: BaseUser) -> dict:
        """
        When a user wants to register for MFA, the client can request a JSON
        response, rather than HTML, if they want to render the UI themselves.
        """
        secret, recovery_codes = await self.secret_table.create_new(
            user_id=user.id, encryption_provider=self.encryption_provider
        )

        qrcode_image = await self._generate_qrcode_image(
            secret=secret, email=user.email
        )

        return {"qrcode_image": qrcode_image, "recovery_codes": recovery_codes}

    async def delete_registration(self, user: BaseUser):
        await self.secret_table.revoke(user_id=user.id)
