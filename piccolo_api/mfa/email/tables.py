from __future__ import annotations

import datetime

from piccolo.columns import Email, Timestamptz, Varchar
from piccolo.table import Table


class EmailCode(Table):
    email = Email()
    code = Varchar()  # TODO - look how best to generate the codes
    created_at = Timestamptz()
    used_at = Timestamptz(null=True, default=None)

    _expiry_time = datetime.timedelta(minutes=5)

    @classmethod
    async def create_new(cls, email: str) -> EmailCode:
        # TODO - generate proper code
        instance = cls({cls.email: email, cls.code: "ABC123"})
        await instance.save()
        return instance

    @classmethod
    async def authenticate(cls, email: str, code: str) -> bool:
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        return await cls.exists().where(
            cls.email == email,
            cls.code == code,
            cls.used_at.is_null(),
            cls.created_at >= now - cls._expiry_time,
        )
