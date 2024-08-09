from __future__ import annotations

import datetime
import logging
import typing as t

from piccolo.columns import Integer, Serial, Text, Timestamptz, Varchar
from piccolo.table import Table

if t.TYPE_CHECKING:
    import pyotp


logger = logging.getLogger(__name__)


def get_pyotp() -> pyotp:
    try:
        import pyotp
    except ImportError as e:
        print(
            "Install pip install piccolo_api[authenticator] to use this "
            "feature."
        )
        raise e

    return pyotp


class AuthenticatorSecret(Table):
    id: Serial  # TODO - we might change this to a UUID primary key
    user_id = Integer(null=False)
    device_name = Varchar(
        null=True,
        default=None,
        help_text=(
            "The user can specify this to make the device memorable, "
            "if we want to allow them to delete secrets."
        ),
    )
    secret = Text(secret=True)
    created_at = Timestamptz()
    revoked_at = Timestamptz(null=True, default=None)
    last_used_at = Timestamptz(null=True, default=None)
    last_used_code = Text(
        null=True,
        default=None,
        help_text=(
            "We store the last used code, to guard against replay attacks."
        ),
    )

    @classmethod
    def generate_secret(cls) -> str:
        pyotp = get_pyotp()
        return pyotp.random_base32()

    @classmethod
    async def create_new(cls, user_id: int) -> AuthenticatorSecret:
        instance = cls(
            {cls.user_id: user_id, cls.secret: cls.generate_secret()}
        )
        await instance.save()
        return instance

    @classmethod
    async def authenticate(cls, user_id: int, code: str) -> bool:
        secrets = await cls.objects().where(
            cls.user_id == user_id,
            cls.revoked_at.is_null(),
        )

        if not secrets:
            return False

        pyotp = get_pyotp()

        # We check all seeds - a user is allowed multiple seeds (i.e. if they
        # have multiple devices).
        for secret in secrets:
            if secret.last_used_code == code:
                logger.warning(
                    f"User {user_id} reused a token - potential replay attack."
                )
                return False

            totp = pyotp.TOTP(secret.secret)

            if totp.verify(code):
                secret.last_used_at = datetime.datetime.now(
                    tz=datetime.timezone.utc
                )
                secret.last_used_code = code
                await secret.save(
                    columns=[cls.last_used_at, cls.last_used_code]
                )

                return True

        return False

    @classmethod
    async def is_user_enrolled(cls, user_id: int) -> bool:
        return await cls.exists().where(cls.user_id == user_id)

    def get_authentication_setup_uri(
        self, email: str, issuer_name: str = "Piccolo-MFA"
    ) -> str:
        pyotp = get_pyotp()

        return pyotp.totp.TOTP(self.secret).provisioning_uri(
            name=email, issuer_name=issuer_name
        )
