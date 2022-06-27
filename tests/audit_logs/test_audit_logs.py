from unittest import TestCase

from piccolo.apps.user.tables import BaseUser
from piccolo.columns import Integer, Varchar
from piccolo.table import Table
from piccolo.utils.sync import run_sync
from starlette.testclient import TestClient

from piccolo_api.audit_logs.commands import clean
from piccolo_api.audit_logs.tables import AuditLog
from piccolo_api.crud.endpoints import PiccoloCRUD


class Movie(Table):
    name = Varchar(length=100, required=True)
    rating = Integer()


class TestSaveAuditLogs(TestCase):
    def setUp(self):
        BaseUser.create_table(if_not_exists=True).run_sync()
        AuditLog.create_table(if_not_exists=True).run_sync()
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        BaseUser.alter().drop_table().run_sync()
        AuditLog.alter().drop_table().run_sync()
        Movie.alter().drop_table().run_sync()

    def test_save_audit_logs(self):
        """
        Make sure a AuditLog post_save_action works.
        """
        user = run_sync(
            BaseUser.create_user(username="admin", password="admin123")
        )
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, audit_log_table=AuditLog)
        )

        json = {"name": "Star Wars", "rating": 93}

        response = client.post("/", json=json)
        run_sync(
            AuditLog.record_save_action(
                Movie, user_id=user.id, new_row_id=response.json()[0]["id"]
            )
        )
        self.assertEqual(response.status_code, 201)

        audit_log = AuditLog.select(AuditLog.action_type).first().run_sync()
        self.assertEqual(audit_log["action_type"], "CREATING")
        self.assertEqual(len(audit_log), 1)


class TestPatchAuditLogs(TestCase):
    def setUp(self):
        BaseUser.create_table(if_not_exists=True).run_sync()
        AuditLog.create_table(if_not_exists=True).run_sync()
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        BaseUser.alter().drop_table().run_sync()
        AuditLog.alter().drop_table().run_sync()
        Movie.alter().drop_table().run_sync()

    def test_patch_audit_logs(self):
        """
        Make sure a AuditLog post_patch_action works.
        """
        user = run_sync(
            BaseUser.create_user(username="admin", password="admin123")
        )

        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, audit_log_table=AuditLog)
        )

        rating = 93
        movie = Movie(name="Star Wars", rating=rating)
        movie.save().run_sync()

        new_name = "Star Wars: A New Hope"

        response = client.patch(f"/{movie.id}/", json={"name": new_name})
        run_sync(
            AuditLog.record_patch_action(
                Movie,
                row_id=movie.id,
                user_id=user.id,
                changes_in_row={"name": new_name},
            )
        )
        self.assertEqual(response.status_code, 200)

        audit_log = AuditLog.select(AuditLog.action_type).first().run_sync()
        self.assertEqual(audit_log["action_type"], "UPDATING")
        self.assertEqual(len(audit_log), 1)


class TestDeleteAuditLogs(TestCase):
    def setUp(self):
        BaseUser.create_table(if_not_exists=True).run_sync()
        AuditLog.create_table(if_not_exists=True).run_sync()
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        BaseUser.alter().drop_table().run_sync()
        AuditLog.alter().drop_table().run_sync()
        Movie.alter().drop_table().run_sync()

    def test_delete_audit_logs(self):
        """
        Make sure a AuditLog post_delete_action works.
        """
        user = run_sync(
            BaseUser.create_user(username="admin", password="admin123")
        )
        client = TestClient(
            PiccoloCRUD(table=Movie, read_only=False, audit_log_table=AuditLog)
        )

        movie = Movie(name="Star Wars", rating=93)
        movie.save().run_sync()

        response = client.delete(f"/{movie.id}/")
        run_sync(
            AuditLog.record_delete_action(
                Movie, row_id=movie.id, user_id=user.id
            )
        )
        self.assertTrue(response.status_code == 204)

        audit_log = AuditLog.select(AuditLog.action_type).first().run_sync()
        self.assertEqual(audit_log["action_type"], "DELETING")
        self.assertEqual(len(audit_log), 1)


class TestCleanAuditLogs(TestCase):
    def setUp(self):
        BaseUser.create_table(if_not_exists=True).run_sync()
        AuditLog.create_table(if_not_exists=True).run_sync()
        Movie.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        BaseUser.alter().drop_table().run_sync()
        AuditLog.alter().drop_table().run_sync()
        Movie.alter().drop_table().run_sync()

    def test_clean_audit_logs(self):
        """
        Make sure a AuditLog clean() method works.
        """
        user = run_sync(
            BaseUser.create_user(username="admin", password="admin123")
        )
        client = TestClient(PiccoloCRUD(table=Movie, read_only=False))

        json = {"name": "Star Wars", "rating": 93}

        response = client.post("/", json=json)

        run_sync(
            AuditLog.record_save_action(
                Movie, user_id=user.id, new_row_id=response.json()[0]["id"]
            )
        )
        self.assertEqual(response.status_code, 201)

        movie = Movie.select().first().run_sync()

        response = client.delete(f"/{movie['id']}/")
        run_sync(
            AuditLog.record_delete_action(
                Movie, row_id=movie["id"], user_id=user.id
            )
        )
        self.assertTrue(response.status_code == 204)

        audit_log = AuditLog.select().run_sync()
        self.assertEqual(len(audit_log), 2)

        run_sync(clean())

        audit_log = AuditLog.select().run_sync()
        self.assertEqual(len(audit_log), 0)
