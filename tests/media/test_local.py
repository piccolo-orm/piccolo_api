import asyncio
import os
import shutil
import tempfile
import uuid
from unittest import TestCase
from unittest.mock import MagicMock, patch

from piccolo.columns.column_types import Array, Varchar
from piccolo.table import Table

from piccolo_api.media.local import LocalMediaStorage


class Movie(Table):
    poster = Varchar()
    screenshots = Array(base_column=Varchar())


class TestLocalMediaStorage(TestCase):
    def setUp(self) -> None:
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_folder_created(self):
        """
        If the media folder doesn't exist, then ``LocalMediaStorage`` should
        try and create it.
        """
        media_path = os.path.join(tempfile.gettempdir(), "randomfolder")

        if os.path.exists(media_path):
            shutil.rmtree(media_path)

        LocalMediaStorage(column=Movie.poster, media_path=media_path)

        self.assertTrue(os.path.exists(media_path))

    @patch("piccolo_api.media.base.uuid")
    def test_store_file(self, uuid_module: MagicMock):
        """
        Make sure we can store files, and retrieve them.
        """
        uuid_module.uuid4.return_value = uuid.UUID(
            "fd0125c7-8777-4976-83c1-81605d5ab155"
        )

        media_path = os.path.join(tempfile.gettempdir(), "piccolo-admin-media")

        if os.path.exists(media_path):
            shutil.rmtree(media_path)

        os.mkdir(media_path)

        storage = LocalMediaStorage(column=Movie.poster, media_path=media_path)

        with open(
            os.path.join(os.path.dirname(__file__), "test_files/bulb.jpg"),
            "rb",
        ) as test_file:
            # Store the file
            file_key = storage.store_file_sync(
                file_name="bulb.jpg", file=test_file
            )

            # Make sure the file was stored.
            self.assertIn(file_key, os.listdir(media_path))

            # Make sure the permissions are correct
            self.assertEqual(
                oct(os.stat(os.path.join(media_path, file_key)).st_mode)[-3:],
                "644",
            )

            # Retrieve the URL for the file
            url = storage.generate_file_url_sync(file_key, root_url="/media/")
            self.assertEqual(
                url, "/media/bulb-fd0125c7-8777-4976-83c1-81605d5ab155.jpg"
            )

            # Retrieve the file itself
            file = asyncio.run(storage.get_file(file_key=file_key))
            assert file is not None
            test_file.seek(0, 0)
            self.assertEqual(file.read(), test_file.read())
            file.close()

            # Make sure that a value is raised if we try saving a file with the
            # same name.
            with self.assertRaises(IOError):
                storage.store_file_sync(file_name="bulb.jpg", file=test_file)

            # List all of the files
            file_list = asyncio.run(storage.get_file_keys())
            self.assertEqual(file_list, [file_key])

            # Delete the file
            asyncio.run(storage.delete_file(file_key=file_key))
            self.assertEqual(os.listdir(storage.media_path), [])

            # Test bulk deletion
            for file_name in ("file_1.txt", "file_2.txt", "file_3.txt"):
                with open(os.path.join(media_path, file_name), "w") as f:
                    f.write("test")

            asyncio.run(
                storage.bulk_delete_files(
                    file_keys=["file_1.txt", "file_2.txt"]
                )
            )

            self.assertListEqual(os.listdir(media_path), ["file_3.txt"])
