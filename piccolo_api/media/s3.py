from __future__ import annotations

import asyncio
import functools
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


class S3MediaStorage(MediaStorage):
    def __init__(
        self,
        column: t.Union[Text, Varchar, Array],
        bucket_name: str,
        folder_name: t.Optional[str] = None,
        connection_kwargs: t.Dict[str, t.Any] = None,
        sign_urls: bool = True,
        signed_url_expiry: int = 3600,
        upload_metadata: t.Dict[str, t.Any] = None,
        executor: t.Optional[Executor] = None,
        allowed_extensions: t.Optional[t.Sequence[str]] = ALLOWED_EXTENSIONS,
        allowed_characters: t.Optional[t.Sequence[str]] = ALLOWED_CHARACTERS,
    ):
        """
        Stores media files in S3 compatible storage. This is a good option when
        you have lots of files to store, and don't want them stored locally
        on a server. Many cloud providers provide S3 compatible storage,
        besides from Amazon Web Services.

        :param column:
            The Piccolo :class:`Column <piccolo.columns.base.Column>` which the
            storage is for.
        :param bucket_name:
            Which S3 bucket the files are stored in.
        :param folder_name:
            The files will be stored in this folder within the bucket. S3
            buckets don't really have folders, but if ``folder`` is
            ``'movie_screenshots'``, then we store the file at
            ``'movie_screenshots/my-file-abc-123.jpeg'``, to simulate it being
            in a folder.
        :param connection_kwargs:
            These kwargs are passed directly to the boto3 :meth:`client <boto3.session.Session.client>`.
            For example::

                S3MediaStorage(
                    ...,
                    connection_kwargs={
                        'aws_access_key_id': 'abc123',
                        'aws_secret_access_key': 'xyz789',
                        'endpoint_url': 's3.cloudprovider.com',
                        'region_name': 'uk'
                    }
                )
        :param sign_urls:
            Whether to sign the URLs - by default this is ``True``, as it's
            highly recommended that your store your files in a private bucket.
        :param signed_url_expiry:
            Files are accessed via signed URLs, which are only valid for this
            number of seconds.
        :param upload_metadata:
            You can provide additional metadata to the uploaded files. To
            see all available options see :class:`S3Transfer.ALLOWED_UPLOAD_ARGS <boto3.s3.transfer.S3Transfer>`.
            Below we show examples of common use cases.

            To set the ACL::

                S3MediaStorage(
                    ...,
                    upload_metadata={'ACL': 'my_acl'}
                )

            To set the content disposition (how the file behaves when opened -
            is it downloaded, or shown in the browser)::

                S3MediaStorage(
                    ...,
                    # Shows the file within the browser:
                    upload_metadata={'ContentDisposition': 'inline'}
                )

            To attach `user defined metadata <https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingMetadata.html>`_
            to the file::

                S3MediaStorage(
                    ...,
                    upload_metadata={'Metadata': {'myfield': 'abc123'}}
                )

            To specify how long browsers should cache the file for::

                S3MediaStorage(
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

        try:
            import boto3  # noqa
        except ImportError:  # pragma: no cover
            sys.exit(
                "Please install boto3 to use this feature "
                "`pip install 'piccolo_api[s3]'`"
            )
        else:
            self.boto3 = boto3

        self.bucket_name = bucket_name
        self.upload_metadata = upload_metadata
        self.folder_name = folder_name
        self.connection_kwargs = connection_kwargs
        self.sign_urls = sign_urls
        self.signed_url_expiry = signed_url_expiry
        self.executor = executor or ThreadPoolExecutor(max_workers=10)

        super().__init__(
            column=column,
            allowed_extensions=allowed_extensions,
            allowed_characters=allowed_characters,
        )

    def get_client(self, config=None):  # pragma: no cover
        """
        Returns an S3 client.
        """
        session = self.boto3.session.Session()
        extra_kwargs = {"config": config} if config else {}
        client = session.client("s3", **self.connection_kwargs, **extra_kwargs)
        return client

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
        client = self.get_client()
        upload_metadata: t.Dict[str, t.Any] = self.upload_metadata or {}

        if extension in CONTENT_TYPE:
            upload_metadata["ContentType"] = CONTENT_TYPE[extension]

        client.upload_fileobj(
            file,
            self.bucket_name,
            self._prepend_folder_name(file_key),
            ExtraArgs=upload_metadata,
        )

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
        if self.sign_urls:
            config = None
        else:
            from botocore import UNSIGNED
            from botocore.config import Config

            config = Config(signature_version=UNSIGNED)

        s3_client = self.get_client(config=config)

        return s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": self._prepend_folder_name(file_key),
            },
            ExpiresIn=self.signed_url_expiry,
        )

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
        s3_client = self.get_client()
        response = s3_client.get_object(
            Bucket=self.bucket_name,
            Key=self._prepend_folder_name(file_key),
        )
        return response["Body"]

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
        s3_client = self.get_client()
        return s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=self._prepend_folder_name(file_key),
        )

    async def bulk_delete_files(self, file_keys: t.List[str]):
        loop = asyncio.get_running_loop()
        func = functools.partial(
            self.bulk_delete_files_sync,
            file_keys=file_keys,
        )
        await loop.run_in_executor(self.executor, func)

    def bulk_delete_files_sync(self, file_keys: t.List[str]):
        s3_client = self.get_client()

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

            s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={
                    "Objects": [
                        {
                            "Key": self._prepend_folder_name(file_key),
                        }
                        for file_key in file_keys
                    ],
                },
            )

            iteration += 1

    def get_file_keys_sync(self) -> t.List[str]:
        """
        Returns the file key for each file we have stored.
        """
        s3_client = self.get_client()

        keys = []
        start_after = None

        while True:
            extra_kwargs: t.Dict[str, t.Any] = {}

            if start_after:
                extra_kwargs["StartAfter"] = start_after

            if self.folder_name:
                extra_kwargs["Prefix"] = f"{self.folder_name}/"

            response = s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                **extra_kwargs,
            )

            contents = response.get("Contents")

            if contents:
                for obj in contents:
                    keys.append(obj["Key"])

                start_after = keys[-1]
            else:
                # https://github.com/nedbat/coveragepy/issues/772
                break  # pragma: no cover

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
                "s3",
                self.connection_kwargs.get("endpoint_url")
                if self.connection_kwargs
                else None,
                self.bucket_name,
                self.folder_name,
            )
        )

    def __eq__(self, value):
        if not isinstance(value, S3MediaStorage):
            return False
        return value.__hash__() == self.__hash__()
