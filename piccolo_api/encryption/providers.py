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


class EncryptionProvider(metaclass=ABCMeta):
    """
    Base class for encryption providers. Don't use it directly, it must be
    subclassed.
    """

    def __init__(self, prefix: str):
        self.prefix = prefix

    @abstractmethod
    def encrypt(self, value: str, add_prefix: bool = True) -> str:
        raise NotImplementedError()

    @abstractmethod
    def decrypt(self, encrypted_value: str, has_prefix: bool = True) -> str:
        raise NotImplementedError()

    def remove_prefix(self, encrypted_value: str) -> str:
        if encrypted_value.startswith(self.prefix):
            return encrypted_value.lstrip(f"{self.prefix}-")
        else:
            raise ValueError(
                "Unable to identify which encryption was used - if moving "
                "to a new encryption provider, use "
                "`migrate_encrypted_value`."
            )

    def add_prefix(self, encrypted_value: str) -> str:
        return f"{self.prefix}-{encrypted_value}"


class PlainTextProvider(EncryptionProvider):
    """
    The values aren't encrypted - can be useful for testing.
    """

    def __init__(self):
        super().__init__(prefix="plain")

    def encrypt(self, value: str, add_prefix: bool = True) -> str:
        return self.add_prefix(value) if add_prefix else value

    def decrypt(self, encrypted_value: str, has_prefix: bool = True) -> str:
        return (
            self.remove_prefix(encrypted_value)
            if has_prefix
            else encrypted_value
        )


class FernetProvider(EncryptionProvider):

    def __init__(self, encryption_key: str):
        """
        Uses the Fernet algorithm for encryption.

        :param encryption_key:
            This can be generated using ``FernetEncryption.get_new_key()``.

        """
        self.encryption_key = encryption_key
        super().__init__(prefix="fernet")

    @staticmethod
    def get_new_key() -> str:
        cryptography = get_cryptography()
        return cryptography.fernet.Fernet.generate_key()  # type: ignore

    def encrypt(self, value: str, add_prefix: bool = True) -> str:
        cryptography = get_cryptography()
        fernet = cryptography.fernet.Fernet(  # type: ignore
            self.encryption_key
        )
        encrypted_value = fernet.encrypt(value.encode("utf8")).decode("utf8")
        return (
            self.add_prefix(encrypted_value=encrypted_value)
            if add_prefix
            else encrypted_value
        )

    def decrypt(self, encrypted_value: str, has_prefix: bool = True) -> str:
        if has_prefix:
            encrypted_value = self.remove_prefix(encrypted_value)

        cryptography = get_cryptography()

        fernet = cryptography.fernet.Fernet(  # type: ignore
            self.encryption_key
        )
        return fernet.decrypt(encrypted_value.encode("utf8")).decode("utf8")


def migrate_encrypted_value(
    old_provider: EncryptionProvider,
    new_provider: EncryptionProvider,
    encrypted_value: str,
):
    """
    If you're migrating from one form of encryption to another, you can use
    this utility.
    """
    return new_provider.encrypt(old_provider.decrypt(encrypted_value))
