from unittest import TestCase

from fastapi import Request
from piccolo.columns import Integer, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from starlette.testclient import TestClient

from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.crud.hooks import Hook, HookType


class Movie(Table):
    name = Varchar(length=100, required=True)
    rating = Integer()

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])


async def set_movie_rating_10(row: Movie):
    row["rating"] = 10
    return row


async def set_movie_rating_20(row: Movie):
    row["rating"] = 20
    return row


async def remove_spaces(row_id: int, values: dict):
    values["name"] = values["name"].replace(" ", "")
    return values


async def look_up_existing(row_id: int, values: dict):
    row = await Movie.objects().get(Movie._meta.primary_key == row_id).run()
    if row is not None:
        values["name"] = row.name
    return values


async def add_additional_name_details(
    row_id: int, values: dict, request: Request
):
    director = request.query_params.get("director_name", "")
    values["name"] = values["name"] + f" ({director})"
    return values


async def additional_name_details(row: Movie, request: Request):
    director = request.query_params.get("director_name", "")
    row["name"] = f"{row.name} ({director})"
    return row


async def raises_exception(row_id: int, request: Request):
    if request.query_params.get("director_name", False):
        raise Exception("Test Passed")


async def failing_hook(row_id: int):
    raise Exception("hook failed")


# TODO - add test for a non-async hook.
class TestPostHooks(TestCase):
    def setUp(self):
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        Movie.alter().drop_table().run_sync()

    def test_request_context_passed_to_post_hook(self):
        """
        Make sure request context can be passed to post hook
        callable
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(
                        hook_type=HookType.pre_save,
                        callable=additional_name_details,
                    )
                ],
            )
        )
        json_req = {
            "name": "Star Wars",
            "rating": 93,
        }
        _ = client.post("/", json=json_req, params={"director_name": "George"})
        movie = Movie.objects().first().run_sync()
        self.assertEqual(movie.name, "Star Wars (George)")

    def test_single_pre_post_hook(self):
        """
        Make sure single hook executes
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(
                        hook_type=HookType.pre_save,
                        callable=set_movie_rating_10,
                    )
                ],
            )
        )
        json_req = {"name": "Star Wars", "rating": 93}
        _ = client.post("/", json=json_req)
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
                        hook_type=HookType.pre_save,
                        callable=set_movie_rating_10,
                    ),
                    Hook(
                        hook_type=HookType.pre_save,
                        callable=set_movie_rating_20,
                    ),
                ],
            )
        )
        json_req = {"name": "Star Wars", "rating": 93}
        _ = client.post("/", json=json_req)
        movie = Movie.objects().first().run_sync()
        self.assertEqual(movie.rating, 20)

    def test_request_context_passed_to_patch_hook(self):
        """
        Make sure request context can be passed to patch hook
        callable
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(
                        hook_type=HookType.pre_patch,
                        callable=add_additional_name_details,
                    )
                ],
            )
        )

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        new_name = "Star Wars: A New Hope"
        new_name_modified = new_name + " (George)"

        json_req = {
            "name": new_name,
        }

        response = client.patch(
            f"/{movie.id}/", json=json_req, params={"director_name": "George"}
        )
        self.assertEqual(response.status_code, 200)

        # Make sure the row is returned:
        response_json = response.json()
        self.assertEqual(response_json["name"], new_name_modified)

        # Make sure the underlying database row was changed:
        movies = Movie.select().run_sync()
        self.assertEqual(movies[0]["name"], new_name_modified)

    def test_pre_patch_hook(self):
        """
        Make sure pre_patch hook executes successfully
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(hook_type=HookType.pre_patch, callable=remove_spaces)
                ],
            )
        )

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        new_name = "Star Wars: A New Hope"
        new_name_modified = new_name.replace(" ", "")

        response = client.patch(f"/{movie.id}/", json={"name": new_name})
        self.assertEqual(response.status_code, 200)

        # Make sure the row is returned:
        response_json = response.json()
        self.assertEqual(response_json["name"], new_name_modified)

        # Make sure the underlying database row was changed:
        movies = Movie.select().run_sync()
        self.assertEqual(movies[0]["name"], new_name_modified)

    def test_pre_patch_hook_db_lookup(self):
        """
        Make sure pre_patch hook can perform db lookups
        (function will always reset "name" to the original name)
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(
                        hook_type=HookType.pre_patch, callable=look_up_existing
                    )
                ],
            )
        )

        original_name = "Star Wars"
        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        new_name = "Star Wars: A New Hope"

        response = client.patch(f"/{movie.id}/", json={"name": new_name})
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertEqual(response_json["name"], original_name)

        movies = Movie.select().run_sync()
        self.assertEqual(movies[0]["name"], original_name)

    def test_request_context_passed_to_delete_hook(self):
        """
        Make sure request context can be passed to patch hook
        callable
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(
                        hook_type=HookType.pre_delete,
                        callable=raises_exception,
                    )
                ],
            )
        )

        movie = Movie(name="Star Wars", rating=10)
        movie.save().run_sync()

        with self.assertRaises(Exception, msg="Test Passed"):
            _ = client.delete(
                f"/{movie.id}/", params={"director_name": "George"}
            )

    def test_delete_hook_fails(self):
        """
        Make sure failing pre_delete hook bubbles up
        (this implicitly also tests that pre_delete hooks execute)
        """
        client = TestClient(
            PiccoloCRUD(
                table=Movie,
                read_only=False,
                hooks=[
                    Hook(hook_type=HookType.pre_delete, callable=failing_hook)
                ],
            )
        )

        movie = Movie(name="Star Wars", rating=10)
        movie.save().run_sync()

        with self.assertRaises(Exception):
            _ = client.delete(f"/{movie.id}/")
