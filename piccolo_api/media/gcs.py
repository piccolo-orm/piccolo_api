from __future__ import annotations

import io
import sys
from collections.abc import Sequence
from datetime import timedelta
from typing import IO, TYPE_CHECKING, Any, Optional, Union

from piccolo.apps.user.tables import BaseUser
from piccolo.columns.column_types import Array, Text, Varchar

from .base import ALLOWED_CHARACTERS, ALLOWED_EXTENSIONS
from .cloud import CloudMediaStorage

if TYPE_CHECKING:  # pragma: no cover
    from concurrent.futures._base import Executor


class GCSMediaStorage(CloudMediaStorage):

    provider_name = "gcs"

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
            Signing a URL requires a private key. Locally that comes from a
            service-account JSON (``GOOGLE_APPLICATION_CREDENTIALS``). On GCP
            compute (e.g. Cloud Run), Application Default Credentials from the
            metadata server have no private key, so we sign via the IAM
            ``signBlob`` API instead - for that to work, grant the runtime
            service account ``roles/iam.serviceAccountTokenCreator`` on itself.
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

        self._client = None

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

    def get_client(self):  # pragma: no cover
        """
        Returns a GCS client. It's cached, because creating one resolves the
        credentials, which on GCP compute means a call to the metadata server
        - and we'd otherwise do that for every file on an admin page.
        """
        if self._client is None:
            self._client = self.storage.Client(**self.connection_kwargs)
        return self._client

    def get_bucket(self):  # pragma: no cover
        return self.get_client().bucket(self.bucket_name)

    def _get_blob(self, file_key: str):
        return self.get_bucket().blob(self._prepend_folder_name(file_key))

    def upload_file(
        self, file_key: str, file: IO, content_type: Optional[str]
    ):
        self._get_blob(file_key).upload_from_file(
            file, content_type=content_type
        )

    def get_signing_kwargs(self) -> dict[str, Any]:
        """
        Signing a URL needs a private key. If the credentials don't have one
        (Application Default Credentials on GCP compute don't), then we have
        to sign via the IAM API instead, which needs the service account's
        email address and an access token.
        """
        from google.auth.credentials import Signing
        from google.auth.transport.requests import Request

        # There's no public accessor for the client's credentials.
        credentials = self.get_client()._credentials

        if isinstance(credentials, Signing):
            # We have a private key, so we can sign locally.
            return {}

        if not credentials.valid:
            credentials.refresh(Request())

        service_account_email = getattr(
            credentials, "service_account_email", None
        )

        if not service_account_email:
            raise ValueError(
                "These credentials can't be used to sign URLs - use a "
                "service account, or pass `sign_urls=False`."
            )

        return {
            "service_account_email": service_account_email,
            "access_token": credentials.token,
        }

    def generate_file_url_sync(
        self, file_key: str, root_url: str, user: Optional[BaseUser] = None
    ) -> str:
        blob = self._get_blob(file_key)

        if not self.sign_urls:
            return blob.public_url

        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=self.signed_url_expiry),
            method="GET",
            **self.get_signing_kwargs(),
        )

    ###########################################################################

    def get_file_sync(self, file_key: str) -> Optional[IO]:
        # `blob.open` would avoid loading the file into memory, but it doesn't
        # touch the network until it's read - so a missing file would raise
        # in the caller rather than here. The other backends raise straight
        # away, so we do the same.
        return io.BytesIO(self._get_blob(file_key).download_as_bytes())

    def delete_file_sync(self, file_key: str):
        return self._get_blob(file_key).delete()

    def bulk_delete_files_sync(self, file_keys: list[str]):
        # `on_error` swallows the `NotFound` raised for a file which has
        # already gone, so that one stale key doesn't abandon the rest of the
        # batch. S3's bulk delete behaves this way too.
        self.get_bucket().delete_blobs(
            [self._prepend_folder_name(i) for i in file_keys],
            on_error=lambda blob: None,
        )

    def get_file_keys_sync(self) -> list[str]:
        blobs = self.get_client().list_blobs(
            self.bucket_name, prefix=self.folder_prefix or None
        )
        return [self._remove_folder_name(blob.name) for blob in blobs]
