from unittest import TestCase

from piccolo_api.shared.auth.user import PiccoloBaseUser, User


class TestUser(TestCase):
    def setUp(self):
        PiccoloBaseUser.create_table(if_not_exists=True).run_sync()

    def tearDown(self):
        PiccoloBaseUser.alter().drop_table(if_exists=True).run_sync()

    def test_user(self):
        """
        Make sure the attributes on the Starlette User map to the correct
        values on the Piccolo user.
        """
        piccolo_user = PiccoloBaseUser(username="bob", password="bob123")
        piccolo_user.save().run_sync()

        starlette_user = User(user=piccolo_user)
        self.assertEqual(starlette_user.user_id, piccolo_user.id)
        self.assertEqual(starlette_user.identity, piccolo_user.id)
        self.assertIsInstance(starlette_user.user_id, int)

        self.assertEqual(starlette_user.username, piccolo_user.username)
        self.assertEqual(starlette_user.username, "bob")
