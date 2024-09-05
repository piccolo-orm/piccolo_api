from __future__ import annotations

import logging
import typing as t
from abc import ABCMeta, abstractmethod

import cryptography.fernet
import nacl.encoding
import nacl.secret

if t.TYPE_CHECKING:
    import cryptography
    import nacl


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
        """
        :param value:
            The value to encrypt.
        :param add_prefix:
            For example, with ``FernetProvider``, it will return a value like:
            ``'fernet-abc123'`` if ``add_prefix=True``. It can be useful to
            have some idea of how the value was encrypted if stored in a
            database.

        """
        raise NotImplementedError()

    @abstractmethod
    def decrypt(self, encrypted_value: str, has_prefix: bool = True) -> str:
        """
        :param encrypted_value:
            The value to decrypt.
        :param has_prefix:
            If the value has a prefix or not, indicating the algorithm used,
            i.e. ``'fernet-abc123'`` or just ``'abc123'``.

        """
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

    def __init__(self, encryption_key: bytes):
        """
        Uses the Fernet algorithm for encryption.

        :param encryption_key:
            This can be generated using ``FernetEncryption.get_new_key()``.

        """
        self.encryption_key = encryption_key
        super().__init__(prefix="fernet")

    @staticmethod
    def get_new_key() -> bytes:
        cryptography = get_cryptography()
        return cryptography.fernet.Fernet.generate_key()  # type: ignore

    def encrypt(self, value: str, add_prefix: bool = True) -> str:
        cryptography = get_cryptography()
        fernet = cryptography.fernet.Fernet(  # type: ignore
            self.encryption_key
        )
        encrypted_value = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
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
        return fernet.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")


def get_nacl_encoding() -> nacl.encoding:  # type: ignore
    try:
        import nacl.encoding
    except ImportError as e:
        print("Install pip install piccolo_api[pynacl] to use this feature.")
        raise e

    return nacl.encoding


def get_nacl_utils() -> nacl.utils:  # type: ignore
    try:
        import nacl.utils
    except ImportError as e:
        print("Install pip install piccolo_api[pynacl] to use this feature.")
        raise e

    return nacl.utils


def get_nacl_secret() -> nacl.secret:  # type: ignore
    try:
        import nacl.secret
    except ImportError as e:
        print("Install pip install piccolo_api[pynacl] to use this feature.")
        raise e

    return nacl.secret


class XChaCha20Provider(EncryptionProvider):

    def __init__(self, encryption_key: bytes):
        """
        Uses the XChaCha20-Poly1305 algorithm for encryption.

        This is more secure than ``FernetProvider``.

        :param encryption_key:
            This can be generated using ``XChaCha20Provider.get_new_key()``.

        """
        self.encryption_key = encryption_key
        super().__init__(prefix="xchacha20")

    @staticmethod
    def get_new_key() -> bytes:
        nacl_utils = get_nacl_utils()
        return nacl_utils.random(nacl.secret.Aead.KEY_SIZE)  # type: ignore

    def _get_nacl_box(self) -> nacl.secret.Aead:
        nacl_secret = get_nacl_secret()
        return nacl_secret.Aead(self.encryption_key)  # type: ignore

    def _get_encoder(self) -> t.Type[nacl.encoding.URLSafeBase64Encoder]:
        nacl_encoding = get_nacl_encoding()
        return nacl_encoding.URLSafeBase64Encoder  # type: ignore

    def encrypt(self, value: str, add_prefix: bool = True) -> str:
        box = self._get_nacl_box()

        encrypted_value = box.encrypt(
            value.encode("utf-8"),
            encoder=self._get_encoder(),
        ).decode("utf-8")

        return (
            self.add_prefix(encrypted_value=encrypted_value)
            if add_prefix
            else encrypted_value
        )

    def decrypt(self, encrypted_value: str, has_prefix: bool = True) -> str:
        if has_prefix:
            encrypted_value = self.remove_prefix(encrypted_value)

        box = self._get_nacl_box()
        return box.decrypt(
            encrypted_value.encode("utf-8"),
            encoder=self._get_encoder(),
        ).decode("utf-8")


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
