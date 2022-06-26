import typing as t
import uuid
from datetime import datetime
from enum import Enum

from piccolo.apps.user.tables import BaseUser
from piccolo.columns import Text, Timestamp, Varchar
from piccolo.table import Table


class AuditLog(Table):
    class ActionType(str, Enum):
        """An enumeration of AuditLog table actions type."""

        CREATING = "CREATING"
        UPDATING = "UPDATING"
        DELETING = "DELETING"

    action_time = Timestamp()
    action_type = Varchar(choices=ActionType)
    action_user = Varchar()
    change_message = Text()

    @classmethod
    async def post_save_action(cls, table: t.Type[Table], user_id: int):
        """
        A method for tracking creating record actions.

        :param table:
            A table for which we monitor activities.
        :param user_id:
            The ``primary key`` of authenticated user.
        """
        result = cls(
            action_time=datetime.now(),
            action_type=cls.ActionType.CREATING,
            action_user=cls.get_user_username(user_id),
            change_message=f"User {cls.get_user_username(user_id)} "
            f"create new row in {table._meta.tablename.title()} table",
        )
        await result.save().run()

    @classmethod
    async def post_patch_action(
        cls,
        table: t.Type[Table],
        row_id: t.Union[str, uuid.UUID, int],
        user_id: int,
    ):
        """
        A method for tracking updating record actions.

        :param table:
            A table for which we monitor activities.
        :param row_id:
            The ``primary key`` of the table for which we
            monitor activities.
        :param user_id:
            The ``primary key`` of authenticated user.
        """
        result = cls(
            action_time=datetime.now(),
            action_type=cls.ActionType.UPDATING,
            action_user=cls.get_user_username(user_id),
            change_message=f"User {cls.get_user_username(user_id)} update row "
            f"{row_id} in {table._meta.tablename.title()} table",
        )
        await result.save().run()

    @classmethod
    async def post_delete_action(
        cls,
        table: t.Type[Table],
        row_id: t.Union[str, uuid.UUID, int],
        user_id: int,
    ):
        """
        A method for tracking deletion record actions.

        :param table:
            A table for which we monitor activities.
        :param row_id:
            The ``primary key`` of the table for which we
            monitor activities.
        :param user_id:
            The ``primary key`` of authenticated user.
        """
        result = cls(
            action_time=datetime.now(),
            action_type=cls.ActionType.DELETING,
            action_user=cls.get_user_username(user_id),
            change_message=f"User {cls.get_user_username(user_id)} delete row "
            f"{row_id} in {table._meta.tablename.title()} table",
        )
        await result.save().run()

    @classmethod
    def get_user_username(cls, user_id: int) -> str:
        """
        Returns the username of authenticated user.

        :param user_id:
            The ``primary key`` of authenticated user.
        """
        user = (
            BaseUser.select(BaseUser.username)
            .where(BaseUser._meta.primary_key == user_id)
            .first()
            .run_sync()
        )
        return user["username"]
