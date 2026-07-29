import asyncio
import os
import uuid
from typing import Optional
from unittest import TestCase
from unittest.mock import MagicMock, patch

from google.auth.credentials import Signing
from google.cloud.exceptions import NotFound
from piccolo.columns.column_types import Varchar
from piccolo.table import Table

from piccolo_api.media.gcs import GCSMediaStorage


class Movie(Table):
    poster = Varchar()


class FakeBatch:
    """
    Mimics :class:`google.cloud.storage.batch.Batch` - crucially, operations
    made while it's open are deferred until it closes, so a test can tell
    whether we're really batching.
    """

    def __init__(self, client: "FakeClient", raise_exception: bool = True):
        self.client = client
        self.raise_exception = raise_exception
        self.operations: list = []

    def __enter__(self):
        self.client.current_batch = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.current_batch = None

        if exc_type is not None:
            return False

        if not self.operations:
            # The real `Batch.finish` rejects an empty batch.
            raise ValueError("No deferred requests")

        errors = []
        for operation in self.operations:
            try:
                operation()
            except NotFound as exception:
                errors.append(exception)

        if errors and self.raise_exception:
            raise errors[-1]

        return False


class FakeBlob:
    def __init__(self, name: str, client: "FakeClient"):
        self.name = name
        self.client = client
        self.public_url = f"https://storage.example.com/{name}"

    @property
    def content_type(self) -> Optional[str]:
        return self.client.content_types.get(self.name)

    def upload_from_file(self, file, content_type=None):
        self.client.content_types[self.name] = content_type
        self.client.store[self.name] = file.read()

    def download_as_bytes(self) -> bytes:
        if self.name not in self.client.store:
            raise NotFound(self.name)
        return self.client.store[self.name]

    def delete(self):
        batch = self.client.current_batch

        if batch is not None:
            batch.operations.append(self._delete)
            return None

        return self._delete()

    def _delete(self):
        # The real client raises if the blob has already gone.
        if self.name not in self.client.store:
            raise NotFound(self.name)
        self.client.store.pop(self.name)
        self.client.content_types.pop(self.name, None)

    def generate_signed_url(self, version, expiration, method, **kwargs):
        self.client.signing_kwargs.update(kwargs)
        return f"https://storage.example.com/{self.name}?signature=abc123"


class FakeBucket:
    def __init__(self, client: "FakeClient"):
        self.client = client

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(name=name, client=self.client)


class FakeCredentials:
    """
    Stands in for Application Default Credentials on GCP compute - i.e. no
    private key, so signing has to go via the IAM API.
    """

    def __init__(self):
        self.valid = True
        self.token = "token123"
        self.service_account_email = "robot@example.iam.gserviceaccount.com"
        self.refreshed = False

    def refresh(self, request):
        self.refreshed = True


class FakeUserCredentials(FakeCredentials):
    """
    A personal Google account - no service account email, so it can't sign.
    """

    def __init__(self):
        super().__init__()
        self.service_account_email = None


class FakeSigningCredentials(Signing):
    """
    A service account with a private key, which can sign locally.
    """

    valid = True

    def sign_bytes(self, message):  # pragma: no cover
        return b"signature"

    @property
    def signer_email(self):  # pragma: no cover
        return "robot@example.iam.gserviceaccount.com"

    @property
    def signer(self):  # pragma: no cover
        return None


class FakeClient:
    def __init__(self, store: dict):
        self.store = store
        self.content_types: dict = {}
        self.signing_kwargs: dict = {}
        self.current_batch: Optional[FakeBatch] = None
        self.batch_count = 0
        self._credentials = FakeCredentials()

    def batch(self, raise_exception: bool = True) -> FakeBatch:
        self.batch_count += 1
        return FakeBatch(client=self, raise_exception=raise_exception)

    def bucket(self, bucket_name: str) -> FakeBucket:
        return FakeBucket(client=self)

    def list_blobs(self, bucket_name: str, prefix=None):
        return [
            self.bucket(bucket_name).blob(name)
            for name in list(self.store)
            if prefix is None or name.startswith(prefix)
        ]


class TestGCSMediaStorage(TestCase):
    def setUp(self) -> None:
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def get_storage(
        self,
        store: dict,
        folder_name="movie_posters",
        **kwargs,
    ) -> GCSMediaStorage:
        storage = GCSMediaStorage(
            column=Movie.poster,
            bucket_name="bucket123",
            folder_name=folder_name,
            **kwargs,
        )
        storage.get_client = MagicMock(  # type: ignore[method-assign]
            return_value=FakeClient(store)
        )
        return storage

    @patch("piccolo_api.media.base.uuid")
    def test_store_and_retrieve(self, uuid_module: MagicMock):
        """
        Store a file, then retrieve its bytes and a signed URL.
        """
        uuid_module.uuid4.return_value = uuid.UUID(
            "fd0125c7-8777-4976-83c1-81605d5ab155"
        )
        store: dict = {}
        storage = self.get_storage(store)

        with open(
            os.path.join(os.path.dirname(__file__), "test_files/bulb.jpg"),
            "rb",
        ) as test_file:
            file_key = asyncio.run(
                storage.store_file(file_name="bulb.jpg", file=test_file)
            )

        self.assertEqual(
            file_key,
            "bulb-fd0125c7-8777-4976-83c1-81605d5ab155.jpg",
        )

        # It was stored under the folder prefix.
        self.assertIn(f"movie_posters/{file_key}", store)

        # The content type was set from the file extension.
        self.assertEqual(
            storage.get_client().content_types[f"movie_posters/{file_key}"],
            "image/jpeg",
        )

        file = asyncio.run(storage.get_file(file_key=file_key))
        assert file is not None
        self.assertEqual(file.read(), store[f"movie_posters/{file_key}"])

        url = asyncio.run(
            storage.generate_file_url(file_key=file_key, root_url="")
        )
        self.assertIn("signature=", url)

    def test_public_url(self):
        storage = self.get_storage({}, sign_urls=False)

        url = asyncio.run(
            storage.generate_file_url(file_key="bulb.jpg", root_url="")
        )
        self.assertEqual(
            url, "https://storage.example.com/movie_posters/bulb.jpg"
        )

    def test_delete_file(self):
        store = {"movie_posters/bulb.jpg": b"data"}
        storage = self.get_storage(store)

        asyncio.run(storage.delete_file(file_key="bulb.jpg"))

        self.assertEqual(store, {})

    def test_bulk_delete_files(self):
        store = {
            "movie_posters/a.jpg": b"a",
            "movie_posters/b.jpg": b"b",
            "movie_posters/c.jpg": b"c",
        }
        storage = self.get_storage(store)

        asyncio.run(storage.bulk_delete_files(file_keys=["a.jpg", "b.jpg"]))

        self.assertEqual(list(store.keys()), ["movie_posters/c.jpg"])

    def test_bulk_delete_is_batched(self):
        """
        Deletes should go out in batches of 100, rather than one request per
        file.
        """
        file_keys = [f"file_{i}.jpg" for i in range(250)]
        store = {f"movie_posters/{i}": b"x" for i in file_keys}
        storage = self.get_storage(store)

        asyncio.run(storage.bulk_delete_files(file_keys=file_keys))

        self.assertEqual(store, {})
        # 250 files, 100 per batch.
        self.assertEqual(storage.get_client().batch_count, 3)

    def test_bulk_delete_no_files(self):
        """
        An empty list shouldn't open a batch - the real client rejects one
        with nothing in it.
        """
        storage = self.get_storage({})

        asyncio.run(storage.bulk_delete_files(file_keys=[]))

        self.assertEqual(storage.get_client().batch_count, 0)

    def test_bulk_delete_ignores_missing_files(self):
        """
        A file which has already gone shouldn't abandon the rest of the batch.
        """
        store = {"movie_posters/a.jpg": b"a", "movie_posters/c.jpg": b"c"}
        storage = self.get_storage(store)

        asyncio.run(
            storage.bulk_delete_files(
                # `b.jpg` isn't there:
                file_keys=["a.jpg", "b.jpg", "c.jpg"]
            )
        )

        self.assertEqual(store, {})

    def test_get_missing_file(self):
        """
        Fetching a file which isn't there should raise straight away, rather
        than handing back a file object which fails when it's read.
        """
        storage = self.get_storage({})

        with self.assertRaises(NotFound):
            asyncio.run(storage.get_file(file_key="missing.jpg"))

    def test_signing_locally_with_a_private_key(self):
        """
        Credentials which can sign (i.e. a service account JSON) need no help
        from the IAM API.
        """
        storage = self.get_storage({})
        storage.get_client()._credentials = FakeSigningCredentials()

        self.assertEqual(storage.get_signing_kwargs(), {})

    def test_expired_credentials_are_refreshed(self):
        storage = self.get_storage({})
        credentials = storage.get_client()._credentials
        credentials.valid = False

        storage.get_signing_kwargs()

        self.assertTrue(credentials.refreshed)

    def test_credentials_which_cant_sign(self):
        """
        A personal Google account has no service account email, so it can't
        sign at all - say so, rather than failing deep in the SDK.
        """
        storage = self.get_storage({})
        storage.get_client()._credentials = FakeUserCredentials()

        with self.assertRaises(ValueError):
            storage.get_signing_kwargs()

    def test_signed_url_uses_iam_api_without_a_private_key(self):
        """
        Credentials with no private key (e.g. on Cloud Run) can't sign
        locally, so we have to pass the service account email and an access
        token, which makes ``generate_signed_url`` use the IAM API.
        """
        store = {"movie_posters/bulb.jpg": b"data"}
        storage = self.get_storage(store)

        asyncio.run(
            storage.generate_file_url(file_key="bulb.jpg", root_url="")
        )

        self.assertEqual(
            storage.get_client().signing_kwargs,
            {
                "service_account_email": (
                    "robot@example.iam.gserviceaccount.com"
                ),
                "access_token": "token123",
            },
        )

    def test_get_file_keys(self):
        store = {
            "movie_posters/a.jpg": b"a",
            "movie_posters/b.jpg": b"b",
        }
        storage = self.get_storage(store)

        keys = asyncio.run(storage.get_file_keys())

        self.assertEqual(sorted(keys), ["a.jpg", "b.jpg"])

    def test_no_folder(self):
        """
        With no ``folder_name``, keys are stored and listed without a prefix.
        """
        store = {"a.jpg": b"a", "b.jpg": b"b"}
        storage = self.get_storage(store, folder_name=None)

        keys = asyncio.run(storage.get_file_keys())
        self.assertEqual(sorted(keys), ["a.jpg", "b.jpg"])

        # Deleting hits the no-folder key path (no prefix prepended).
        asyncio.run(storage.delete_file(file_key="a.jpg"))
        self.assertEqual(sorted(store.keys()), ["b.jpg"])
