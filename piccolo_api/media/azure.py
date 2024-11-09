from __future__ import annotations

import asyncio
import datetime
import functools
import io
import os
import pathlib
import sys
import typing as t
from concurrent.futures import ThreadPoolExecutor

from piccolo.apps.user.tables import BaseUser
from piccolo.columns.column_types import Array, Text, Varchar

from .base import ALLOWED_CHARACTERS, ALLOWED_EXTENSIONS, MediaStorage
from .content_type import CONTENT_TYPE

if t.TYPE_CHECKING:  # pragma: no cover
    from concurrent.futures._base import Executor

try:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import (
        BlobSasPermissions,
        BlobServiceClient,
        ContainerClient,
        generate_blob_sas,
    )

    azure_import_successful = True
except ImportError:  # pragma: no cover
    azure_import_successful = False


class AzureMediaStorage(MediaStorage):
    def __init__(
        self,
        column: t.Union[Text, Varchar, Array],
        storage_account_name: str,
        container_name: str,
        folder_name: t.Optional[str] = None,
        connection_kwargs: t.Optional[t.Dict[str, t.Any]] = None,
        sign_urls: bool = True,
        signed_url_expiry: int = 3600,
        upload_metadata: t.Optional[t.Dict[str, t.Any]] = None,
        executor: t.Optional[Executor] = None,
        allowed_extensions: t.Optional[t.Sequence[str]] = ALLOWED_EXTENSIONS,
        allowed_characters: t.Optional[t.Sequence[str]] = ALLOWED_CHARACTERS,
    ):
        """
        Stores media files in Azure Blob Storage. This is a good option when
        you have lots of files to store, and don't want them stored locally
        on a server.

        To use a connection string, either specify the
        "AZURE_STORAGE_CONNECTION_STRING" environment variable or add
        "connection_string" to the connection_kwargs attribute. If these
        don't exist then the Azure SDK will use the DefaultAzureCredential
        class to look through various locations for credentials like
        environment variables, workload identities etc...

        :param column:
            The Piccolo :class:`Column <piccolo.columns.base.Column>` which the
            storage is for.
        :param storage_account_name:
            Which Azure storage account the files are stored in.
        :param container_name:
            The container within the storage account which files are stored within.
        :param folder_name:
            The files will be stored in this folder within the bucket. Azure Blob Storage
            don't really have folders, but if ``folder`` is
            ``'movie_screenshots'``, then we store the file at
            ``'movie_screenshots/my-file-abc-123.jpeg'``, to simulate it being
            in a folder.
        :param connection_kwargs:
            To use a connection string from Blob Storage rather than DefaultAzureCredential().
            For example::

                AzureMediaStorage(
                    ...,
                    connection_kwargs={
                        'connection_string': 'DefaultEndpointsProtocol=https;AccountName=name;AccountKey=key;EndpointSuffix=core.windows.net'
                    }
                )
        :param sign_urls:
            Whether to sign the URLs - by default this is ``True``, as it's
            highly recommended that your store your files in a private bucket.
        :param signed_url_expiry:
            Files are accessed via signed URLs, which are only valid for this
            number of seconds.
        :param upload_metadata:
            You can provide additional metadata to the uploaded files.
            Below we show examples of common use cases.

            To set object Metadata::

                AzureMediaStorage(
                    ...,
                    upload_metadata={'SomeMetadataTag': 'SomeMetadataValue'}
                )

            To set the content disposition (how the file behaves when opened -
            is it downloaded, or shown in the browser)::

                AzureMediaStorage(
                    ...,
                    # Shows the file within the browser:
                    upload_metadata={'ContentDisposition': 'inline'}
                )

            To specify how long browsers should cache the file for::

                AzureMediaStorage(
                    ...,
                    # Cache the file for 24 hours:
                    upload_metadata={'CacheControl': 'max-age=86400'}
                )

            Note: We automatically add the ``ContentType`` field based on the
            file type.
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
        """  # noqa: E501
        if not azure_import_successful:
            sys.exit(
                "Please install azure-storage-blob and azure-identity "
                "to use this feature `pip install 'piccolo_api[azure]'`"
            )

        self.storage_account_name = storage_account_name
        self.container_name = container_name
        self.upload_metadata = upload_metadata or {}
        self.folder_name = folder_name
        self.connection_kwargs = connection_kwargs or {}
        self.sign_urls = sign_urls
        self.signed_url_expiry = signed_url_expiry
        self.executor = executor or ThreadPoolExecutor(max_workers=10)

        self.connection_string = None
        self.connection_string_parts: t.Dict[str, str] = {}
        if "connection_string" in self.connection_kwargs:
            self.connection_string = self.connection_kwargs[
                "connection_string"
            ]
        elif "AZURE_STORAGE_CONNECTION_STRING" in os.environ:
            self.connection_string = os.environ[
                "AZURE_STORAGE_CONNECTION_STRING"
            ]
        if self.connection_string:
            self.connection_string_parts = dict(
                pair.split("=", 1)
                for pair in self.connection_string.split(";")
            )
            if "AccountKey" not in self.connection_string_parts:
                sys.exit(
                    "Specified connection string did not contain AccountKey"
                )

        super().__init__(
            column=column,
            allowed_extensions=allowed_extensions,
            allowed_characters=allowed_characters,
        )

    def get_client(
        self,
    ) -> t.Tuple["ContainerClient", "BlobServiceClient"]:  # pragma: no cover
        """
        Returns an Azure client.
        """
        if self.connection_string:
            blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        else:
            account_url = (
                f"https://{self.storage_account_name}.blob.core.windows.net"
            )

            # DefaultAzureCredential is not part of the BlobServiceClient types
            default_credential = t.cast(str, DefaultAzureCredential())

            blob_service_client = BlobServiceClient(
                account_url, credential=default_credential
            )

        container_client = blob_service_client.get_container_client(
            self.container_name
        )

        return container_client, blob_service_client

    async def store_file(
        self, file_name: str, file: t.IO, user: t.Optional[BaseUser] = None
    ) -> str:
        loop = asyncio.get_running_loop()

        blocking_function = functools.partial(
            self.store_file_sync, file_name=file_name, file=file, user=user
        )

        file_key = await loop.run_in_executor(self.executor, blocking_function)

        return file_key

    def _prepend_folder_name(self, file_key: str) -> str:
        folder_name = self.folder_name
        if folder_name:
            return str(pathlib.Path(folder_name, file_key))
        else:
            return file_key

    def store_file_sync(
        self, file_name: str, file: t.IO, user: t.Optional[BaseUser] = None
    ) -> str:
        """
        A sync wrapper around :meth:`store_file`.
        """
        file_key = self.generate_file_key(file_name=file_name, user=user)
        extension = file_key.rsplit(".", 1)[-1]
        client, _ = self.get_client()
        upload_metadata: t.Dict[str, t.Any] = self.upload_metadata.copy()

        if extension in CONTENT_TYPE:
            upload_metadata["ContentType"] = CONTENT_TYPE[extension]

        blob_client = client.get_blob_client(
            self._prepend_folder_name(file_key)
        )

        blob_client.upload_blob(data=file, metadata=upload_metadata)

        return file_key

    async def generate_file_url(
        self, file_key: str, root_url: str, user: t.Optional[BaseUser] = None
    ) -> str:
        """
        This retrieves an absolute URL for the file.
        """
        loop = asyncio.get_running_loop()

        blocking_function: t.Callable = functools.partial(
            self.generate_file_url_sync,
            file_key=file_key,
            root_url=root_url,
            user=user,
        )

        return await loop.run_in_executor(self.executor, blocking_function)

    def generate_file_url_sync(
        self, file_key: str, root_url: str, user: t.Optional[BaseUser] = None
    ) -> str:
        """
        A sync wrapper around :meth:`generate_file_url`.
        """
        blob_name = self._prepend_folder_name(file_key)

        if not self.sign_urls:
            return (
                f"https://{self.storage_account_name}.blob.core.windows.net/"
                f"{self.container_name}/{blob_name}"
            )

        _, blob_service_client = self.get_client()

        now = datetime.datetime.now(datetime.timezone.utc)
        expiry = now + datetime.timedelta(seconds=self.signed_url_expiry)

        account_key = None
        user_delegation_key = None
        if self.connection_string:
            account_key = self.connection_string_parts["AccountKey"]
        else:
            user_delegation_key = blob_service_client.get_user_delegation_key(
                now, now + datetime.timedelta(hours=1)
            )

        sas_token = generate_blob_sas(
            account_name=self.storage_account_name,
            container_name=self.container_name,
            blob_name=self._prepend_folder_name(file_key),
            permission=BlobSasPermissions(read=True),
            account_key=account_key,
            user_delegation_key=user_delegation_key,
            expiry=expiry,
        )

        sas_url = (
            f"https://{self.storage_account_name}.blob.core.windows.net/"
            f"{self.container_name}/{blob_name}?{sas_token}"
        )
        return sas_url

    ###########################################################################

    async def get_file(self, file_key: str) -> t.Optional[t.IO]:
        """
        Returns the file object matching the ``file_key``.
        """
        loop = asyncio.get_running_loop()

        func = functools.partial(self.get_file_sync, file_key=file_key)

        return await loop.run_in_executor(self.executor, func)

    def get_file_sync(self, file_key: str) -> t.Optional[t.IO]:
        """
        Returns the file object matching the ``file_key``.
        """
        client, _ = self.get_client()
        blob_client = client.get_blob_client(
            self._prepend_folder_name(file_key)
        )

        container = io.BytesIO()
        blob_client.download_blob().readinto(container)
        container.seek(0)

        return container

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
        client, _ = self.get_client()
        blob_client = client.get_blob_client(
            self._prepend_folder_name(file_key)
        )

        blob_client.delete_blob()

    async def bulk_delete_files(self, file_keys: t.List[str]):
        loop = asyncio.get_running_loop()
        func = functools.partial(
            self.bulk_delete_files_sync,
            file_keys=file_keys,
        )
        await loop.run_in_executor(self.executor, func)

    def bulk_delete_files_sync(self, file_keys: t.List[str]):
        client, _ = self.get_client()

        batch_size = 100
        iteration = 0

        while True:
            batch = file_keys[
                (iteration * batch_size) : (  # noqa: E203
                    iteration + 1 * batch_size
                )
            ]
            if not batch:
                # https://github.com/nedbat/coveragepy/issues/772
                break  # pragma: no cover

            client.delete_blobs(
                {
                    self._prepend_folder_name(file_key): None
                    for file_key in file_keys
                }
            )

            iteration += 1

    def get_file_keys_sync(self) -> t.List[str]:
        """
        Returns the file key for each file we have stored.
        """
        client, _ = self.get_client()

        keys = []

        kwargs = {}
        if self.folder_name:
            kwargs["name_starts_with"] = self.folder_name
        for key_name in client.list_blob_names(**kwargs):  # type: str
            keys.append(key_name)

        if self.folder_name:
            prefix = f"{self.folder_name}/"
            return [i.lstrip(prefix) for i in keys]
        else:
            return keys

    async def get_file_keys(self) -> t.List[str]:
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
                "azure",
                self.storage_account_name,
                self.container_name,
                self.connection_string,
                self.folder_name,
            )
        )

    def __eq__(self, value):
        if not isinstance(value, AzureMediaStorage):
            return False
        return value.__hash__() == self.__hash__()
