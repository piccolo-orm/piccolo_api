from __future__ import annotations

import datetime
import logging
import typing as t

import cryptography.fernet
from piccolo.apps.user.tables import BaseUser
from piccolo.columns import Array, Integer, Serial, Text, Timestamptz, Varchar
from piccolo.table import Table

from piccolo_api.mfa.recovery_codes import generate_recovery_code

if t.TYPE_CHECKING:
    import cryptography
    import pyotp


logger = logging.getLogger(__name__)


def get_pyotp() -> pyotp:  # type: ignore
    try:
        import pyotp
    except ImportError as e:
        print(
            "Install pip install piccolo_api[authenticator] to use this "
            "feature."
        )
        raise e

    return pyotp


def get_cryptography() -> cryptography:  # type: ignore
    try:
        import cryptography
    except ImportError as e:
        print(
            "Install pip install piccolo_api[authenticator] to use this "
            "feature."
        )
        raise e

    return cryptography


def _encrypt(value: str, db_encryption_key: str) -> str:
    cryptography = get_cryptography()
    fernet = cryptography.fernet.Fernet(db_encryption_key)  # type: ignore
    encrypted_value = fernet.encrypt(value.encode("utf8"))
    return encrypted_value.decode("utf8")


def _decrypt(encrypted_value: str, db_encryption_key: str) -> str:
    cryptography = get_cryptography()
    fernet = cryptography.fernet.Fernet(db_encryption_key)  # type: ignore
    value = fernet.decrypt(encrypted_value.encode("utf8"))
    return value.decode("utf8")


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
        return pyotp.random_base32()  # type: ignore

    @classmethod
    async def create_new(
        cls,
        user_id: int,
        db_encryption_key: str,
        recovery_code_count: int = 8,
    ) -> t.Tuple[AuthenticatorSecret, t.List[str]]:
        """
        Returns the new ``AuthenticatorSecret`` and the unhashed recovery
        codes. This is the only time the unhashed recovery codes will be
        accessible.

        :param user_id:
            The user to create the secret for.
        :param db_encryption_key:
            The secret is encrypted in the database - ``db_encryption_key``
            can be any reasonably random string. It provides a little extra
            protection vs storing the secret in plain text.
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
        encrypted_secret = _encrypt(
            value=secret, db_encryption_key=db_encryption_key
        )

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
    async def authenticate(
        cls, user_id: int, code: str, db_encryption_key: str
    ) -> bool:
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

        shared_secret = _decrypt(
            encrypted_value=secret.secret, db_encryption_key=db_encryption_key
        )
        totp = pyotp.TOTP(shared_secret)  # type: ignore

        if totp.verify(code):
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
        return await cls.exists().where(cls.user_id == user_id)

    def get_authentication_setup_uri(
        self,
        email: str,
        db_encryption_key: str,
        issuer_name: str = "Piccolo-MFA",
    ) -> str:
        pyotp = get_pyotp()

        shared_secret = _decrypt(
            encrypted_value=self.secret, db_encryption_key=db_encryption_key
        )

        return pyotp.totp.TOTP(shared_secret).provisioning_uri(  # type: ignore
            name=email, issuer_name=issuer_name
        )
