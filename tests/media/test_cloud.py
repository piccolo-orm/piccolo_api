from unittest import TestCase

from piccolo.columns.column_types import Varchar
from piccolo.table import Table

from piccolo_api.media.gcs import GCSMediaStorage
from piccolo_api.media.s3 import S3MediaStorage


class Movie(Table):
    poster = Varchar()


class TestEquality(TestCase):
    """
    Make sure ``CloudMediaStorage`` subclasses are only equal when they point
    at the same place.
    """

    def test_same_backend(self):
        self.assertEqual(
            S3MediaStorage(
                column=Movie.poster,
                bucket_name="bucket123",
                folder_name="movie_posters",
            ),
            S3MediaStorage(
                column=Movie.poster,
                bucket_name="bucket123",
                folder_name="movie_posters",
            ),
        )

    def test_different_provider(self):
        """
        A GCS bucket and an S3 bucket can share a name, but they're not the
        same bucket.
        """
        self.assertNotEqual(
            S3MediaStorage(
                column=Movie.poster,
                bucket_name="bucket123",
                folder_name="movie_posters",
            ),
            GCSMediaStorage(
                column=Movie.poster,
                bucket_name="bucket123",
                folder_name="movie_posters",
            ),
        )

    def test_different_endpoint(self):
        """
        S3 compatible storage from different providers can share a bucket
        name, so the endpoint has to be part of the comparison.
        """
        self.assertNotEqual(
            S3MediaStorage(
                column=Movie.poster,
                bucket_name="bucket123",
                connection_kwargs={"endpoint_url": "s3.provider-a.com"},
            ),
            S3MediaStorage(
                column=Movie.poster,
                bucket_name="bucket123",
                connection_kwargs={"endpoint_url": "s3.provider-b.com"},
            ),
        )

    def test_different_folder(self):
        self.assertNotEqual(
            S3MediaStorage(
                column=Movie.poster,
                bucket_name="bucket123",
                folder_name="movie_posters",
            ),
            S3MediaStorage(
                column=Movie.poster,
                bucket_name="bucket123",
                folder_name="movie_screenshots",
            ),
        )
