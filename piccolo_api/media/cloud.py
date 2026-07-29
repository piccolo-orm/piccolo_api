from __future__ import annotations

import abc
import asyncio
import functools
import pathlib
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import IO, TYPE_CHECKING, Any, Optional, Union

from piccolo.apps.user.tables import BaseUser
from piccolo.columns.column_types import Array, Text, Varchar

from .base import ALLOWED_CHARACTERS, ALLOWED_EXTENSIONS, MediaStorage

if TYPE_CHECKING:  # pragma: no cover
    from concurrent.futures._base import Executor


class CloudMediaStorage(MediaStorage):
    """
    Base class for object storage backends, such as
    :class:`S3MediaStorage <piccolo_api.media.s3.S3MediaStorage>` and
    :class:`GCSMediaStorage <piccolo_api.media.gcs.GCSMediaStorage>`.

    The cloud SDKs are blocking, so each operation has a ``_sync`` method
    which does the actual work, and an async method which runs it in an
    executor to keep the event loop free. This class provides the async
    methods - a subclass just has to implement the ``_sync`` ones, and set
    :attr:`provider_name`.
    """

    #: Identifies the backend when hashing / comparing instances, so that two
    #: backends pointing at a bucket of the same name aren't considered equal.
    provider_name: str

    def __init__(
        self,
        column: Union[Text, Varchar, Array],
        bucket_name: str,
        folder_name: Optional[str] = None,
        connection_kwargs: Optional[dict[str, Any]] = None,
        sign_urls: bool = True,
        signed_url_expiry: int = 3600,
        executor: Optional[Executor] = None,
        allowed_extensions: Optional[Sequence[str]] = ALLOWED_EXTENSIONS,
        allowed_characters: Optional[Sequence[str]] = ALLOWED_CHARACTERS,
    ):
        self.bucket_name = bucket_name
        self.folder_name = folder_name
        self.connection_kwargs = connection_kwargs or {}
        self.sign_urls = sign_urls
        self.signed_url_expiry = signed_url_expiry
        self.executor = executor or ThreadPoolExecutor(max_workers=10)

        super().__init__(
            column=column,
            allowed_extensions=allowed_extensions,
            allowed_characters=allowed_characters,
        )

    def _prepend_folder_name(self, file_key: str) -> str:
        folder_name = self.folder_name
        if folder_name:
            return str(pathlib.Path(folder_name, file_key))
        else:
            return file_key

    async def _run_sync(self, func, **kwargs):
        """
        Runs a blocking ``_sync`` method in the executor.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, functools.partial(func, **kwargs)
        )

    ###########################################################################

    async def store_file(
        self, file_name: str, file: IO, user: Optional[BaseUser] = None
    ) -> str:
        return await self._run_sync(
            self.store_file_sync, file_name=file_name, file=file, user=user
        )

    @abc.abstractmethod
    def store_file_sync(
        self, file_name: str, file: IO, user: Optional[BaseUser] = None
    ) -> str:
        """
        A sync version of :meth:`store_file`.
        """
        raise NotImplementedError  # pragma: no cover

    async def generate_file_url(
        self, file_key: str, root_url: str, user: Optional[BaseUser] = None
    ) -> str:
        """
        This retrieves an absolute URL for the file.
        """
        return await self._run_sync(
            self.generate_file_url_sync,
            file_key=file_key,
            root_url=root_url,
            user=user,
        )

    @abc.abstractmethod
    def generate_file_url_sync(
        self, file_key: str, root_url: str, user: Optional[BaseUser] = None
    ) -> str:
        """
        A sync version of :meth:`generate_file_url`.
        """
        raise NotImplementedError  # pragma: no cover

    async def get_file(self, file_key: str) -> Optional[IO]:
        """
        Returns the file object matching the ``file_key``.
        """
        return await self._run_sync(self.get_file_sync, file_key=file_key)

    @abc.abstractmethod
    def get_file_sync(self, file_key: str) -> Optional[IO]:
        """
        A sync version of :meth:`get_file`.
        """
        raise NotImplementedError  # pragma: no cover

    async def delete_file(self, file_key: str):
        """
        Deletes the file object matching the ``file_key``.
        """
        return await self._run_sync(self.delete_file_sync, file_key=file_key)

    @abc.abstractmethod
    def delete_file_sync(self, file_key: str):
        """
        A sync version of :meth:`delete_file`.
        """
        raise NotImplementedError  # pragma: no cover

    async def bulk_delete_files(self, file_keys: list[str]):
        await self._run_sync(self.bulk_delete_files_sync, file_keys=file_keys)

    @abc.abstractmethod
    def bulk_delete_files_sync(self, file_keys: list[str]):
        """
        A sync version of :meth:`bulk_delete_files`.
        """
        raise NotImplementedError  # pragma: no cover

    async def get_file_keys(self) -> list[str]:
        """
        Returns the file key for each file we have stored.
        """
        return await self._run_sync(self.get_file_keys_sync)

    @abc.abstractmethod
    def get_file_keys_sync(self) -> list[str]:
        """
        A sync version of :meth:`get_file_keys`.
        """
        raise NotImplementedError  # pragma: no cover

    ###########################################################################

    def _hash_components(self) -> tuple:
        """
        The values which make this storage unique. A subclass can add to these
        - for example, S3 compatible storage can have a custom endpoint.
        """
        return (self.provider_name, self.bucket_name, self.folder_name)

    def __hash__(self):
        return hash(self._hash_components())

    def __eq__(self, value):
        if not isinstance(value, type(self)):
            return False
        return value.__hash__() == self.__hash__()
