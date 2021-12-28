import json
from unittest import TestCase

from piccolo.columns import Integer, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import (
    PiccoloCRUD,
)
from piccolo_api.crud.hooks import Hook, HookType


class Movie(Table):
    name = Varchar(length=100, required=True)
    rating = Integer()

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])


async def set_movie_rating_10(row: Movie):
    row.rating = 10
    return row


async def set_movie_rating_20(row: Movie):
    row.rating = 20
    return row


async def remove_spaces(row_id: int, values: dict):
    values["name"] = values["name"].replace(" ", "")
    return values


async def look_up_existing(row_id: int, values: dict):
    row = await Movie.objects().get(Movie.id == row_id).run()
    values["name"] = row.name
    return values


async def failing_hook(row_id: int):
    raise Exception("hook failed")


class TestPostHooks(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_single_pre_post_hook(self):
        """
        Make sure single hook executes
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(hook_type=HookType.pre_save, coro=set_movie_rating_10)
                ],
            )
        )
        json = {"name": "Star Wars", "rating": 93}
        response = client.post("/", json=json)
        movie = Movie.objects().first().run_sync()
        self.assertEqual(movie.rating, 10)

    def test_multi_pre_post_hooks(self):
        """
        Make sure multiple hooks execute in correct order
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(
                        hook_type=HookType.pre_save, coro=set_movie_rating_10
                    ),
                    Hook(
                        hook_type=HookType.pre_save, coro=set_movie_rating_20
                    ),
                ],
            )
        )
        json = {"name": "Star Wars", "rating": 93}
        response = client.post("/", json=json)
        movie = Movie.objects().first().run_sync()
        self.assertEqual(movie.rating, 20)

    def test_pre_patch_hook(self):
        """
        Make sure pre_patch hook executes successfully
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[Hook(hook_type=HookType.pre_patch, coro=remove_spaces)],
            )
        )

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        new_name = "Star Wars: A New Hope"
        new_name_modified = new_name.replace(" ", "")

        response = client.patch(f"/{movie.id}/", json={"name": new_name})
        self.assertTrue(response.status_code == 200)

        # Make sure the row is returned:
        response_json = json.loads(response.json())
        self.assertTrue(response_json["name"] == new_name_modified)

        # Make sure the underlying database row was changed:
        movies = Movie.select().run_sync()
        self.assertTrue(movies[0]["name"] == new_name_modified)

    def test_pre_patch_hook_db_lookup(self):
        """
        Make sure pre_patch hook can perform db lookups (function will always reset "name" to the original name)
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(hook_type=HookType.pre_patch, coro=look_up_existing)
                ],
            )
        )

        original_name = "Star Wars"
        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        new_name = "Star Wars: A New Hope"

        response = client.patch(f"/{movie.id}/", json={"name": new_name})
        self.assertTrue(response.status_code == 200)

        response_json = json.loads(response.json())
        self.assertTrue(response_json["name"] == original_name)

        movies = Movie.select().run_sync()
        self.assertTrue(movies[0]["name"] == original_name)

    def test_delete_hook_fails(self):
        """
        Make sure failing pre_delete hook bubbles up (this implicitly also tests that pre_delete hooks execute)
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[Hook(hook_type=HookType.pre_delete, coro=failing_hook)],
            )
        )

        movie = Movie(name="Star Wars", rating=10)
        movie.save().run_sync()

        with self.assertRaises(Exception):
            response = client.delete(f"/{movie.id}/")
