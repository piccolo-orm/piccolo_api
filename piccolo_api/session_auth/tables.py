from __future__ import annotations

from datetime import datetime, timedelta
import secrets
import typing as t

from asgiref.sync import async_to_sync
from piccolo.table import Table
from piccolo.columns import Varchar, Timestamp, Integer


def future() -> datetime:
    return datetime.now() + timedelta(hours=1)


def max_expiry_date() -> datetime:
    """
    We set a hard limit on the expiry date - it can keep on getting extended
    up until this value, after which it's best to invalidate it, and either
    require login again, or just create a new session token.
    """
    return datetime.now() + timedelta(days=7)


class SessionsBase(Table, tablename="sessions"):
    """
    Inherit from this table for a session store.
    """

    token = Varchar(length=100, null=False)
    user_id = Integer(null=False)
    expiry_date = Timestamp(default=future, null=False)
    max_expiry_date = Timestamp(default=max_expiry_date, null=False)

    @classmethod
    async def create_session(
        cls, user_id: int, expiry_date: t.Optional[datetime] = None
    ) -> SessionsBase:
        while True:
            token = secrets.token_urlsafe(nbytes=32)
            if not await cls.exists().where(cls.token == token).run():
                break

        session = cls(token=token, user_id=user_id)
        if expiry_date:
            session.expiry_date = expiry_date

        await session.save().run()

        return session

    @classmethod
    def create_session_sync(
        cls, user_id: int, expiry_date: t.Optional[datetime] = None
    ) -> SessionsBase:
        return async_to_sync(cls.create_session)(user_id, expiry_date)

    @classmethod
    async def get_user_id(cls, token: str) -> t.Optional[int]:
        """
        Returns the user_id if the given token is valid, otherwise None.
        """
        try:
            session: SessionsBase = await cls.objects().where(
                cls.token == token
            ).first().run()
        except ValueError:
            return None

        now = datetime.now()
        if (session.expiry_date > now) and (session.max_expiry_date > now):
            return session.user_id
        else:
            return None

    @classmethod
    def get_user_id_sync(cls, token: str) -> t.Optional[int]:
        return async_to_sync(cls.get_user_id)(token)

    @classmethod
    async def remove_session(cls, token: str):
        await cls.delete().where(cls.token == token).run()

    @classmethod
    def remove_session_sync(cls, token: str):
        return async_to_sync(cls.remove_session)(token)
