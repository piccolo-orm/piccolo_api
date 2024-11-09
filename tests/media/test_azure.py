import asyncio
import io
import uuid
from unittest import TestCase
from unittest.mock import ANY, MagicMock, patch

from piccolo.columns.column_types import Array, Varchar
from piccolo.table import Table

from piccolo_api.media.azure import AzureMediaStorage


class Movie(Table):
    poster = Varchar()
    screenshots = Array(base_column=Varchar())


class TestAzureMediaStorage(TestCase):
    def setUp(self) -> None:
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    @patch("piccolo_api.media.azure.generate_blob_sas")
    @patch("piccolo_api.media.base.uuid")
    @patch("piccolo_api.media.azure.AzureMediaStorage.get_client")
    def test_store_file(
        self,
        get_client: MagicMock,
        uuid_module: MagicMock,
        generate_mock: MagicMock,
    ):
        """
        Make sure we can store files, and retrieve them.
        """
        uuid_module.uuid4.return_value = uuid.UUID(
            "fd0125c7-8777-4976-83c1-81605d5ab155"
        )
        storage_account_name = "bucket123"
        container_name = "c1"
        folder_name = "movie_posters"
        connection_kwargs = {"connection_string": "Blah=2134;AccountKey=1234"}

        blob_client = MagicMock()
        container_client = MagicMock()
        blob_service_client = MagicMock()

        container_client.get_blob_client.return_value = blob_client

        get_client.return_value = container_client, blob_service_client

        storage = AzureMediaStorage(
            column=Movie.poster,
            storage_account_name=storage_account_name,
            container_name=container_name,
            folder_name=folder_name,
            connection_kwargs=connection_kwargs,
            upload_metadata={
                "Metadata": {"visibility": "premium"},
                "CacheControl": "max-age=86400",
            },
        )

        # Store the file
        file_content = io.BytesIO()
        file_key = asyncio.run(
            storage.store_file(file_name="bulb.jpg", file=file_content)
        )

        blob_client.upload_blob.assert_called_with(
            data=file_content, metadata=ANY
        )
        blob_client.reset_mock()

        generate_mock.return_value = "token1234"

        # Retrieve the URL for the file
        url = asyncio.run(storage.generate_file_url(file_key, root_url=""))

        expected_url = (
            f"https://{storage_account_name}.blob.core.windows.net/"
            f"{container_name}/{folder_name}/{file_key}?token1234"
        )

        self.assertEqual(url, expected_url)
        generate_mock.reset_mock()

        class StreamDownloader:
            def readinto(self, fp: io.BytesIO):
                fp.write(b"12345678")

        blob_client.download_blob.return_value = StreamDownloader()
        # Get the file
        file = asyncio.run(storage.get_file(file_key=file_key))
        assert file is not None
        self.assertEqual(file.read(), b"12345678")

        container_client.list_blob_names.return_value = [file_key]

        # List file keys
        file_keys = asyncio.run(storage.get_file_keys())
        self.assertListEqual(file_keys, [file_key])

        # Delete the file
        asyncio.run(storage.delete_file(file_key=file_key))

        blob_client.delete_blob.assert_called_once()

        # Test bulk deletion
        asyncio.run(
            storage.bulk_delete_files(
                file_keys=["file_1.txt", "file_2.txt", "file_3.txt"]
            )
        )

        container_client.delete_blobs.assert_called_with(
            {
                f"{folder_name}/file_1.txt": None,
                f"{folder_name}/file_2.txt": None,
                f"{folder_name}/file_3.txt": None,
            }
        )

    @patch("piccolo_api.media.azure.generate_blob_sas")
    @patch("piccolo_api.media.base.uuid")
    @patch("piccolo_api.media.azure.AzureMediaStorage.get_client")
    def test_unsigned(
        self,
        get_client: MagicMock,
        uuid_module: MagicMock,
        generate_mock: MagicMock,
    ):
        """
        Make sure we can enable unsigned URLs if requested.
        """

        uuid_module.uuid4.return_value = uuid.UUID(
            "fd0125c7-8777-4976-83c1-81605d5ab155"
        )
        storage_account_name = "bucket123"
        container_name = "c1"
        folder_name = "movie_posters"
        connection_kwargs = {"connection_string": "Blah=2134;AccountKey=1234"}

        blob_client = MagicMock()
        container_client = MagicMock()
        blob_service_client = MagicMock()

        container_client.get_blob_client.return_value = blob_client

        get_client.return_value = container_client, blob_service_client

        storage = AzureMediaStorage(
            column=Movie.poster,
            storage_account_name=storage_account_name,
            container_name=container_name,
            folder_name=folder_name,
            connection_kwargs=connection_kwargs,
            sign_urls=False,
            upload_metadata={
                "Metadata": {"visibility": "premium"},
                "CacheControl": "max-age=86400",
            },
        )

        # Store the file
        file = io.BytesIO()
        file_key = asyncio.run(
            storage.store_file(file_name="bulb.jpg", file=file)
        )

        blob_client.upload_blob.assert_called_with(data=file, metadata=ANY)
        blob_client.reset_mock()

        # Retrieve the URL for the file
        url = asyncio.run(storage.generate_file_url(file_key, root_url=""))

        generate_mock.assert_not_called()

        expected_url = (
            f"https://{storage_account_name}.blob.core.windows.net/"
            f"{container_name}/{folder_name}/{file_key}"
        )

        self.assertEqual(url, expected_url)

    @patch("piccolo_api.media.azure.generate_blob_sas")
    @patch("piccolo_api.media.base.uuid")
    @patch("piccolo_api.media.azure.AzureMediaStorage.get_client")
    def test_no_folder(
        self,
        get_client: MagicMock,
        uuid_module: MagicMock,
        generate_mock: MagicMock,
    ):
        """
        Make sure we can store files, and retrieve them when the
        ``folder_name`` is ``None``.
        """
        uuid_module.uuid4.return_value = uuid.UUID(
            "fd0125c7-8777-4976-83c1-81605d5ab155"
        )
        storage_account_name = "bucket123"
        container_name = "c1"
        connection_kwargs = {"connection_string": "Blah=2134;AccountKey=1234"}

        blob_client = MagicMock()
        container_client = MagicMock()
        blob_service_client = MagicMock()

        container_client.get_blob_client.return_value = blob_client

        get_client.return_value = container_client, blob_service_client

        storage = AzureMediaStorage(
            column=Movie.poster,
            storage_account_name=storage_account_name,
            container_name=container_name,
            connection_kwargs=connection_kwargs,
            upload_metadata={
                "Metadata": {"visibility": "premium"},
                "CacheControl": "max-age=86400",
            },
        )

        # Store the file
        file_content = io.BytesIO()
        file_key = asyncio.run(
            storage.store_file(file_name="bulb.jpg", file=file_content)
        )

        blob_client.upload_blob.assert_called_with(
            data=file_content, metadata=ANY
        )
        blob_client.reset_mock()

        generate_mock.return_value = "token1234"

        # Retrieve the URL for the file
        url = asyncio.run(storage.generate_file_url(file_key, root_url=""))

        expected_url = (
            f"https://{storage_account_name}.blob.core.windows.net/"
            f"{container_name}/{file_key}?token1234"
        )

        self.assertEqual(url, expected_url)
        generate_mock.reset_mock()

        class StreamDownloader:
            def readinto(self, fp: io.BytesIO):
                fp.write(b"12345678")

        blob_client.download_blob.return_value = StreamDownloader()
        # Get the file
        file = asyncio.run(storage.get_file(file_key=file_key))
        assert file is not None
        self.assertEqual(file.read(), b"12345678")

        container_client.list_blob_names.return_value = [file_key]

        # List file keys
        file_keys = asyncio.run(storage.get_file_keys())
        self.assertListEqual(file_keys, [file_key])

        # Delete the file
        asyncio.run(storage.delete_file(file_key=file_key))

        blob_client.delete_blob.assert_called_once()

        # Test bulk deletion
        asyncio.run(
            storage.bulk_delete_files(
                file_keys=["file_1.txt", "file_2.txt", "file_3.txt"]
            )
        )

        container_client.delete_blobs.assert_called_with(
            {"file_1.txt": None, "file_2.txt": None, "file_3.txt": None}
        )


class TestFolderName(TestCase):
    """
    Make sure the folder name is correctly added to the file key.
    """

    def test_with_folder_name(self):
        storage = AzureMediaStorage(
            column=Movie.poster,
            storage_account_name="test_bucket",
            container_name="test_container",
            folder_name="test_folder",
            connection_kwargs={},
        )
        self.assertEqual(
            storage._prepend_folder_name(file_key="abc123.jpeg"),
            "test_folder/abc123.jpeg",
        )

    def test_without_folder_name(self):
        storage = AzureMediaStorage(
            column=Movie.poster,
            storage_account_name="test_bucket",
            container_name="test_container",
            folder_name=None,
            connection_kwargs={},
        )
        self.assertEqual(
            storage._prepend_folder_name(file_key="abc123.jpeg"),
            "abc123.jpeg",
        )
