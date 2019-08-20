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


class SessionsBase(Table):
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
