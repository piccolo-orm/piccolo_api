from __future__ import annotations

from piccolo.columns import Email, Timestamptz, Varchar
from piccolo.table import Table


class EmailCode(Table):
    email = Email()
    code = Varchar()  # TODO - look how best to generate the codes
    created_at = Timestamptz()
    used_at = Timestamptz(null=True, default=None)

    @classmethod
    async def create_new(cls, email: str) -> EmailCode:
        # TODO - generate proper code
        instance = cls({cls.email: email, cls.code: "ABC123"})
        await instance.save()
        return instance
