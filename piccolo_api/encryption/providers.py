from __future__ import annotations

import logging
import typing as t
from abc import ABCMeta, abstractmethod

import cryptography.fernet

if t.TYPE_CHECKING:
    import cryptography


logger = logging.getLogger(__name__)


def get_cryptography() -> cryptography:  # type: ignore
    try:
        import cryptography
    except ImportError as e:
        print(
            "Install pip install piccolo_api[cryptography] to use this "
            "feature."
        )
        raise e

    return cryptography


class EncryptionProvider(meta=ABCMeta):
    """
    Base class for encryption providers. Don't use it directly, it must be
    subclassed.
    """

    def __init__(self, prefix: str):
        self.prefix = prefix

    @abstractmethod
    def encrypt(self, value: str, *args, **kwargs) -> str:
        raise NotImplementedError()

    @abstractmethod
    def decrypt(self, value: str, *args, **kwargs) -> str:
        raise NotImplementedError()


class PlainTextProvider(EncryptionProvider):
    """
    Store the 
    """

    def __init__(self):
        super.__init__(prefix="plain")

    def encrypt(self, value: str, *args, **kwargs) -> str:
        return value

    def decrypt(self, value: str, *args, **kwargs) -> str:
        return value


class FernetProvider(EncryptionProvider):

    def __init__(self, encryption_key: str):
        """
        :param db_encryption_key:
            This can be generated using ``FernetEncryption.get_new_key()``.

        """
        self.encryption_key = encryption_key
        super.__init__(prefix="fernet")

    @staticmethod
    def get_new_key() -> str:
        cryptography = get_cryptography()
        return cryptography.fernet.Fernet.generate_key()  # type: ignore

    def encrypt(
        self, value: str, use_prefix: bool = True, *args, **kwargs
    ) -> str:
        cryptography = get_cryptography()
        fernet = cryptography.fernet.Fernet(  # type: ignore
            self.encryption_key
        )
        encrypted_value = fernet.encrypt(value.encode("utf8")).decode("utf8")
        return (
            f"{self.prefix}-{encrypted_value}"
            if use_prefix
            else encrypted_value
        )

    def decrypt(
        self, encrypted_value: str, use_prefix: bool = True, *args, **kwargs
    ) -> str:
        cryptography = get_cryptography()

        if use_prefix:
            if encrypted_value.startswith(self.prefix):
                encrypted_value = encrypted_value.lstrip(f"{self.prefix}-")
            else:
                raise ValueError(
                    "Unable to identify which encryption was used - if moving "
                    "to a new encryption provider, use "
                    "`migrate_encrypted_value`."
                )

        fernet = cryptography.fernet.Fernet(  # type: ignore
            self.encryption_key
        )
        value = fernet.decrypt(encrypted_value.encode("utf8"))
        return value.decode("utf8")


async def migrate_encrypted_value(
    old_provider: EncryptionProvider,
    new_provider: EncryptionProvider,
    encrypted_value: str,
):
    """
    If you're migrating from one form of encryption to another, you can use
    this utility.
    """
    return new_provider.encrypt(old_provider.decrypt(encrypted_value))
