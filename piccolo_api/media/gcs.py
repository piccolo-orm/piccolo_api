from __future__ import annotations

import asyncio
import functools
import io
import pathlib
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import IO, TYPE_CHECKING, Any, Optional, Union

from piccolo.apps.user.tables import BaseUser
from piccolo.columns.column_types import Array, Text, Varchar

from .base import ALLOWED_CHARACTERS, ALLOWED_EXTENSIONS, MediaStorage
from .content_type import CONTENT_TYPE

if TYPE_CHECKING:  # pragma: no cover
    from concurrent.futures._base import Executor


class GCSMediaStorage(MediaStorage):
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
        """
        Stores media files in Google Cloud Storage. This is a good option when
        you have lots of files to store, and don't want them stored locally on
        a server.

        :param column:
            The Piccolo :class:`Column <piccolo.columns.base.Column>` which the
            storage is for.
        :param bucket_name:
            Which GCS bucket the files are stored in.
        :param folder_name:
            The files will be stored in this folder within the bucket. GCS
            buckets don't really have folders, but if ``folder`` is
            ``'movie_screenshots'``, then we store the file at
            ``'movie_screenshots/my-file-abc-123.jpeg'``, to simulate it being
            in a folder.
        :param connection_kwargs:
            These kwargs are passed directly to the
            :class:`google.cloud.storage.Client`. For example::

                GCSMediaStorage(
                    ...,
                    connection_kwargs={'project': 'my-gcp-project'}
                )
        :param sign_urls:
            Whether to sign the URLs - by default this is ``True``, as it's
            highly recommended that you store your files in a private bucket.
        :param signed_url_expiry:
            Files are accessed via signed URLs, which are only valid for this
            number of seconds.
        :param executor:
            An executor, which file save operations are run in, to avoid
            blocking the event loop. If not specified, we use a sensibly
            configured :class:`ThreadPoolExecutor <concurrent.futures.ThreadPoolExecutor>`.
        :param allowed_extensions:
            Which file extensions are allowed. If ``None``, then all extensions
            are allowed (not recommended unless the users are trusted).
        :param allowed_characters:
            Which characters are allowed in the file name. By default, it's
            very strict. If set to ``None`` then all characters are allowed.

        .. note::
            Generating signed URLs requires a private key. Locally, this comes
            from a service-account JSON (``GOOGLE_APPLICATION_CREDENTIALS``). On
            GCP compute (e.g. Cloud Run), Application Default Credentials from
            the metadata server have no private key, so signing must go through
            the IAM ``signBlob`` API - grant the runtime service account
            ``roles/iam.serviceAccountTokenCreator`` on itself.
        """  # noqa: E501

        try:
            from google.cloud import storage  # noqa
        except ImportError:  # pragma: no cover
            sys.exit(
                "Please install google-cloud-storage to use this feature "
                "`pip install 'piccolo_api[gcs]'`"
            )
        else:
            self.storage = storage

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

    def get_client(self):  # pragma: no cover
        """
        Returns a GCS client.
        """
        return self.storage.Client(**self.connection_kwargs)

    def get_bucket(self):  # pragma: no cover
        return self.get_client().bucket(self.bucket_name)

    def _prepend_folder_name(self, file_key: str) -> str:
        folder_name = self.folder_name
        if folder_name:
            return str(pathlib.Path(folder_name, file_key))
        else:
            return file_key

    async def store_file(
        self, file_name: str, file: IO, user: Optional[BaseUser] = None
    ) -> str:
        loop = asyncio.get_running_loop()

        blocking_function = functools.partial(
            self.store_file_sync, file_name=file_name, file=file, user=user
        )

        file_key = await loop.run_in_executor(self.executor, blocking_function)

        return file_key

    def store_file_sync(
        self, file_name: str, file: IO, user: Optional[BaseUser] = None
    ) -> str:
        """
        A sync wrapper around :meth:`store_file`.
        """
        file_key = self.generate_file_key(file_name=file_name, user=user)
        extension = file_key.rsplit(".", 1)[-1]

        blob = self.get_bucket().blob(self._prepend_folder_name(file_key))

        content_type = CONTENT_TYPE.get(extension)

        blob.upload_from_file(file, content_type=content_type)

        return file_key

    async def generate_file_url(
        self, file_key: str, root_url: str, user: Optional[BaseUser] = None
    ) -> str:
        """
        This retrieves an absolute URL for the file.
        """
        loop = asyncio.get_running_loop()

        blocking_function: Callable = functools.partial(
            self.generate_file_url_sync,
            file_key=file_key,
            root_url=root_url,
            user=user,
        )

        return await loop.run_in_executor(self.executor, blocking_function)

    def generate_file_url_sync(
        self, file_key: str, root_url: str, user: Optional[BaseUser] = None
    ) -> str:
        """
        A sync wrapper around :meth:`generate_file_url`.
        """
        blob = self.get_bucket().blob(self._prepend_folder_name(file_key))

        if not self.sign_urls:
            return blob.public_url

        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=self.signed_url_expiry),
            method="GET",
        )

    ###########################################################################

    async def get_file(self, file_key: str) -> Optional[IO]:
        """
        Returns the file object matching the ``file_key``.
        """
        loop = asyncio.get_running_loop()

        func = functools.partial(self.get_file_sync, file_key=file_key)

        return await loop.run_in_executor(self.executor, func)

    def get_file_sync(self, file_key: str) -> Optional[IO]:
        """
        Returns the file object matching the ``file_key``.
        """
        blob = self.get_bucket().blob(self._prepend_folder_name(file_key))
        return io.BytesIO(blob.download_as_bytes())

    async def delete_file(self, file_key: str):
        """
        Deletes the file object matching the ``file_key``.
        """
        loop = asyncio.get_running_loop()

        func = functools.partial(
            self.delete_file_sync,
            file_key=file_key,
        )

        return await loop.run_in_executor(self.executor, func)

    def delete_file_sync(self, file_key: str):
        """
        Deletes the file object matching the ``file_key``.
        """
        blob = self.get_bucket().blob(self._prepend_folder_name(file_key))
        return blob.delete()

    async def bulk_delete_files(self, file_keys: list[str]):
        loop = asyncio.get_running_loop()
        func = functools.partial(
            self.bulk_delete_files_sync,
            file_keys=file_keys,
        )
        await loop.run_in_executor(self.executor, func)

    def bulk_delete_files_sync(self, file_keys: list[str]):
        bucket = self.get_bucket()
        for file_key in file_keys:
            bucket.blob(self._prepend_folder_name(file_key)).delete()

    def get_file_keys_sync(self) -> list[str]:
        """
        Returns the file key for each file we have stored.
        """
        client = self.get_client()

        prefix = f"{self.folder_name}/" if self.folder_name else None

        blobs = client.list_blobs(self.bucket_name, prefix=prefix)

        keys = [blob.name for blob in blobs]

        if prefix:
            return [key[len(prefix) :] for key in keys]  # noqa: E203
        else:
            return keys

    async def get_file_keys(self) -> list[str]:
        """
        Returns the file key for each file we have stored.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, self.get_file_keys_sync
        )

    def __hash__(self):
        return hash(
            (
                "gcs",
                self.bucket_name,
                self.folder_name,
            )
        )

    def __eq__(self, value):
        if not isinstance(value, GCSMediaStorage):
            return False
        return value.__hash__() == self.__hash__()
