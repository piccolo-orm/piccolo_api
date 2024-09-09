from __future__ import annotations

import datetime
import logging
import typing as t

from piccolo.apps.user.tables import BaseUser
from piccolo.columns import Array, Integer, Serial, Text, Timestamptz
from piccolo.table import Table

from piccolo_api.encryption.providers import EncryptionProvider
from piccolo_api.mfa.recovery_codes import generate_recovery_code

if t.TYPE_CHECKING:  # pragma: no cover
    import pyotp


logger = logging.getLogger(__name__)


def get_pyotp() -> pyotp:  # type: ignore  # pragma: no cover
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
    id: Serial
    user_id = Integer(null=False)
    secret = Text(secret=True)
    recovery_codes = Array(
        Text(),
        help_text="Used to gain temporary access, if they lose their phone.",
        secret=True,
    )
    recovery_codes_used_at = Array(
        Timestamptz(),
        help_text="Whenever a recovery code is used, store a timestamp here.",
    )
    created_at = Timestamptz()
    revoked_at = Timestamptz(
        null=True,
        default=None,
        help_text=(
            "If set, this instance should be considered unusable for "
            "authentication purposes."
        ),
    )
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
        return pyotp.random_base32()  # type: ignore

    @classmethod
    async def create_new(
        cls,
        user_id: int,
        encryption_provider: EncryptionProvider,
        recovery_code_count: int = 8,
    ) -> t.Tuple[AuthenticatorSecret, t.List[str]]:
        """
        Returns the new ``AuthenticatorSecret`` and the unhashed recovery
        codes. This is the only time the unhashed recovery codes will be
        accessible.

        :param user_id:
            The user to create the secret for.
        :param encryption_provider:
            Determines how the secret is stored in the database.
        :param recovery_code_count:
            How many recovery codes to generate for the user - this allows
            them to still gain access if their phone is lost.

        """
        # Generate recovery codes

        recovery_codes = [
            generate_recovery_code() for _ in range(recovery_code_count)
        ]

        #######################################################################
        # Hash the recovery codes

        # Use the hashing logic from BaseUser.
        # We want to use the same salt for all of the user's recovery codes,
        # otherwise logging in using a recovery code will take a long time.
        salt = BaseUser.get_salt()

        hashed_recovery_codes = [
            BaseUser.hash_password(password=recovery_code, salt=salt)
            for recovery_code in recovery_codes
        ]

        #######################################################################
        # Generate a shared secret

        secret = cls.generate_secret()

        # We'll encrypt the secret for storing in the database.
        encrypted_secret = encryption_provider.encrypt(value=secret)

        #######################################################################

        instance = cls(
            {
                cls.user_id: user_id,
                cls.secret: encrypted_secret,
                cls.recovery_codes: hashed_recovery_codes,
            }
        )
        await instance.save()

        return (instance, recovery_codes)

    @classmethod
    async def revoke(cls, user_id: int):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        await cls.update({cls.revoked_at: now}).where(
            cls.user_id == user_id,
            cls.revoked_at.is_null(),
        )

    @classmethod
    async def authenticate(
        cls,
        user_id: int,
        code: str,
        encryption_provider: EncryptionProvider,
        valid_window: int = 0,
    ) -> bool:
        """
        :param valid_window:
            Extends the validity to this many counter ticks before and after
            the current one.

        """
        secret = (
            await cls.objects()
            .where(
                cls.user_id == user_id,
                cls.revoked_at.is_null(),
            )
            .order_by(cls.created_at, ascending=False)
            .first()
        )

        if secret is None:
            return False

        pyotp = get_pyotp()

        if secret.last_used_code == code:
            logger.warning(
                f"User {user_id} reused a token - potential replay attack."
            )
            return False

        shared_secret = encryption_provider.decrypt(
            encrypted_value=secret.secret
        )
        totp = pyotp.TOTP(shared_secret)  # type: ignore

        if totp.verify(code, valid_window=valid_window):
            secret.last_used_at = datetime.datetime.now(
                tz=datetime.timezone.utc
            )
            secret.last_used_code = code
            await secret.save(columns=[cls.last_used_at, cls.last_used_code])

            return True

        #######################################################################
        # Check recovery code

        # Do a sanity check that it's roughly long enough.
        if len(code) > 10 and (recovery_codes := secret.recovery_codes):
            first_recovery_code = recovery_codes[0]

            # Get the algorithm, salt etc - they should be the same for each
            # of the user's recovery codes, to save overhead.
            _, iterations_, salt, _ = BaseUser.split_stored_password(
                password=first_recovery_code
            )

            hashed_code = BaseUser.hash_password(
                password=code,
                salt=salt,
                iterations=int(iterations_),
            )

            for recovery_code in recovery_codes:
                if recovery_code == hashed_code:
                    # Remove the recovery code, and record when it was used.
                    secret.recovery_codes = [
                        i for i in recovery_codes if i != recovery_code
                    ]
                    secret.recovery_codes_used_at.append(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    await secret.save(
                        columns=[
                            cls.recovery_codes,
                            cls.recovery_codes_used_at,
                        ]
                    )

                    return True

        return False

    @classmethod
    async def is_user_enrolled(cls, user_id: int) -> bool:
        return await cls.exists().where(
            cls.user_id == user_id, cls.revoked_at.is_null()
        )

    def get_authentication_setup_uri(
        self,
        email: str,
        encryption_provider: EncryptionProvider,
        issuer_name: str = "Piccolo-MFA",
    ) -> str:
        pyotp = get_pyotp()

        shared_secret = encryption_provider.decrypt(
            encrypted_value=self.secret
        )

        return pyotp.totp.TOTP(shared_secret).provisioning_uri(  # type: ignore
            name=email, issuer_name=issuer_name
        )
