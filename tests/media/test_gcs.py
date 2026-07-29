import asyncio
import io
import os
import uuid
from typing import IO, Optional
from unittest import TestCase
from unittest.mock import MagicMock, patch

from piccolo.columns.column_types import Varchar
from piccolo.table import Table

from piccolo_api.media.gcs import GCSMediaStorage


class Movie(Table):
    poster = Varchar()


class FakeBlob:
    def __init__(self, name: str, store: dict, content_types: dict):
        self.name = name
        self.store = store
        self.content_types = content_types
        self.public_url = f"https://storage.example.com/{name}"

    @property
    def content_type(self) -> Optional[str]:
        return self.content_types.get(self.name)

    def upload_from_file(self, file, content_type=None):
        self.content_types[self.name] = content_type
        self.store[self.name] = file.read()

    def open(self, mode: str) -> IO:
        return io.BytesIO(self.store[self.name])

    def delete(self):
        self.store.pop(self.name, None)
        self.content_types.pop(self.name, None)

    def generate_signed_url(self, version, expiration, method):
        return f"https://storage.example.com/{self.name}?signature=abc123"


class FakeBucket:
    def __init__(self, store: dict, content_types: dict):
        self.store = store
        self.content_types = content_types

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(
            name=name, store=self.store, content_types=self.content_types
        )


class FakeClient:
    def __init__(self, store: dict):
        self.store = store
        self.content_types: dict = {}

    def bucket(self, bucket_name: str) -> FakeBucket:
        return FakeBucket(store=self.store, content_types=self.content_types)

    def list_blobs(self, bucket_name: str, prefix=None):
        return [
            self.bucket(bucket_name).blob(name)
            for name in self.store
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
