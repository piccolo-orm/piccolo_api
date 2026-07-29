from __future__ import annotations

import sys
import threading
from collections.abc import Sequence
from typing import IO, TYPE_CHECKING, Any, Optional, Union

from piccolo.apps.user.tables import BaseUser
from piccolo.columns.column_types import Array, Text, Varchar

from .base import ALLOWED_CHARACTERS, ALLOWED_EXTENSIONS
from .cloud import CloudMediaStorage

if TYPE_CHECKING:  # pragma: no cover
    from concurrent.futures._base import Executor


class S3MediaStorage(CloudMediaStorage):

    provider_name = "s3"

    def __init__(
        self,
        column: Union[Text, Varchar, Array],
        bucket_name: str,
        folder_name: Optional[str] = None,
        connection_kwargs: Optional[dict[str, Any]] = None,
        sign_urls: bool = True,
        signed_url_expiry: int = 3600,
        upload_metadata: Optional[dict[str, Any]] = None,
        executor: Optional[Executor] = None,
        allowed_extensions: Optional[Sequence[str]] = ALLOWED_EXTENSIONS,
        allowed_characters: Optional[Sequence[str]] = ALLOWED_CHARACTERS,
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

        self.upload_metadata = upload_metadata or {}
        self._client = None
        self._unsigned_client = None
        # Reentrant, because `get_unsigned_client` calls `get_client`.
        self._client_lock = threading.RLock()

        super().__init__(
            column=column,
            bucket_name=bucket_name,
            folder_name=folder_name,
            connection_kwargs=connection_kwargs,
            sign_urls=sign_urls,
            signed_url_expiry=signed_url_expiry,
            executor=executor,
            allowed_extensions=allowed_extensions,
            allowed_characters=allowed_characters,
        )

    def get_client(self, config=None):
        """
        Returns an S3 client.

        The default client is cached, because building one creates a boto3
        session, which parses botocore's service and endpoint data - we'd
        otherwise do that for every file shown on a page. A client with a
        custom ``config`` isn't cached, as we don't know what's in it.
        """
        with self._client_lock:
            if config is None and self._client is not None:
                return self._client

            session = self.boto3.session.Session()
            extra_kwargs = {"config": config} if config else {}
            client = session.client(
                "s3", **self.connection_kwargs, **extra_kwargs
            )

            if config is None:
                self._client = client

            return client

    def get_unsigned_client(self):
        """
        Returns a client which generates unsigned URLs. Cached, for the same
        reason as :meth:`get_client`.
        """
        with self._client_lock:
            if self._unsigned_client is None:
                from botocore import UNSIGNED
                from botocore.config import Config

                self._unsigned_client = self.get_client(
                    config=Config(signature_version=UNSIGNED)
                )

            return self._unsigned_client

    def upload_file(
        self, file_key: str, file: IO, content_type: Optional[str]
    ):
        upload_metadata: dict[str, Any] = {**self.upload_metadata}

        if content_type:
            upload_metadata["ContentType"] = content_type

        self.get_client().upload_fileobj(
            file,
            self.bucket_name,
            self._prepend_folder_name(file_key),
            ExtraArgs=upload_metadata,
        )

    def generate_file_url_sync(
        self, file_key: str, root_url: str, user: Optional[BaseUser] = None
    ) -> str:
        s3_client = (
            self.get_client() if self.sign_urls else self.get_unsigned_client()
        )

        return s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": self._prepend_folder_name(file_key),
            },
            ExpiresIn=self.signed_url_expiry,
        )

    ###########################################################################

    def get_file_sync(self, file_key: str) -> Optional[IO]:
        s3_client = self.get_client()
        response = s3_client.get_object(
            Bucket=self.bucket_name,
            Key=self._prepend_folder_name(file_key),
        )
        return response["Body"]

    def delete_file_sync(self, file_key: str):
        s3_client = self.get_client()
        return s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=self._prepend_folder_name(file_key),
        )

    def bulk_delete_files_sync(self, file_keys: list[str]):
        s3_client = self.get_client()

        # `delete_objects` rejects requests with more than 1000 keys, so we
        # stay comfortably below that.
        batch_size = 100

        for start in range(0, len(file_keys), batch_size):
            batch = file_keys[start : start + batch_size]  # noqa: E203

            s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={
                    "Objects": [
                        {
                            "Key": self._prepend_folder_name(file_key),
                        }
                        for file_key in batch
                    ],
                },
            )

    def get_file_keys_sync(self) -> list[str]:
        s3_client = self.get_client()

        keys = []
        start_after = None

        while True:
            extra_kwargs: dict[str, Any] = {}

            if start_after:
                extra_kwargs["StartAfter"] = start_after

            if self.folder_prefix:
                extra_kwargs["Prefix"] = self.folder_prefix

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

        return [self._remove_folder_name(i) for i in keys]

    ###########################################################################

    def _hash_components(self) -> tuple:
        return (
            *super()._hash_components(),
            self.connection_kwargs.get("endpoint_url"),
        )
