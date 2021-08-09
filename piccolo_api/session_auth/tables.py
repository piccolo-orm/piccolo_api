from __future__ import annotations

import secrets
import typing as t
from datetime import datetime, timedelta

from piccolo.columns import Integer, Timestamp, Varchar
from piccolo.columns.defaults.timestamp import TimestampOffset
from piccolo.table import Table
from piccolo.utils.sync import run_sync


class SessionsBase(Table, tablename="sessions"):
    """
    Use this table, or inherit from it, to create for a session store.

    We set a hard limit on the expiry date - it can keep on getting extended
    up until this value, after which it's best to invalidate it, and either
    require login again, or just create a new session token.
    """

    token = Varchar(length=100, null=False)
    user_id = Integer(null=False)
    expiry_date: t.Union[Timestamp, datetime] = Timestamp(
        default=TimestampOffset(hours=1), null=False
    )
    max_expiry_date: t.Union[Timestamp, datetime] = Timestamp(
        default=TimestampOffset(days=7), null=False
    )

    @classmethod
    async def create_session(
        cls,
        user_id: int,
        expiry_date: t.Optional[datetime] = None,
        max_expiry_date: t.Optional[datetime] = None,
    ) -> SessionsBase:
        while True:
            token = secrets.token_urlsafe(nbytes=32)
            if not await cls.exists().where(cls.token == token).run():
                break

        session = cls(token=token, user_id=user_id)
        if expiry_date:
            session.expiry_date = expiry_date
        if max_expiry_date:
            session.max_expiry_date = max_expiry_date

        await session.save().run()

        return session

    @classmethod
    def create_session_sync(
        cls, user_id: int, expiry_date: t.Optional[datetime] = None
    ) -> SessionsBase:
        return run_sync(cls.create_session(user_id, expiry_date))

    @classmethod
    async def get_user_id(
        cls, token: str, increase_expiry: t.Optional[timedelta] = None
    ) -> t.Union[int, t.Any]:
        """
        Returns the user_id if the given token is valid, otherwise None.

        :param increase_expiry:
            If set, the `expiry_date` will be increased by the given amount
            if it's close to expiring. If it has already expired, nothing
            happens. The `max_expiry_date` remains the same, so there's a hard
            limit on how long a session can be used for.
        """
        session: SessionsBase = (
            await cls.objects().where(cls.token == token).first().run()
        )

        if not session:
            return None

        now = datetime.now()
        if (session.expiry_date > now) and (session.max_expiry_date > now):
            if increase_expiry and (
                t.cast(datetime, session.expiry_date) - now < increase_expiry
            ):
                session.expiry_date = (
                    t.cast(datetime, session.expiry_date) + increase_expiry
                )
                await session.save().run()

            return session.user_id
        else:
            return None

    @classmethod
    def get_user_id_sync(cls, token: str) -> t.Optional[int]:
        return run_sync(cls.get_user_id(token))

    @classmethod
    async def remove_session(cls, token: str):
        await cls.delete().where(cls.token == token).run()

    @classmethod
    def remove_session_sync(cls, token: str):
        return run_sync(cls.remove_session(token))
