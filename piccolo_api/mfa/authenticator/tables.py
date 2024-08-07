from __future__ import annotations

import datetime

from piccolo.columns import Integer, Serial, Text, Timestamptz
from piccolo.table import Table


def get_pyotp():
    try:
        import pyotp
    except ImportError as e:
        print(
            "Install pip install piccolo_api[authenticator] to use this "
            "feature."
        )
        raise e

    return pyotp


class AuthenticatorSeed(Table):
    id: Serial
    user_id = Integer(null=False)
    code = Text()
    revoked_at = Timestamptz(null=True, default=None)
    created_at = Timestamptz()
    last_used_at = Timestamptz()

    @classmethod
    async def create_new(cls, user_id: int) -> AuthenticatorSeed:
        # TODO - generate proper code
        instance = cls({cls.user_id: user_id, cls.code: "ABC123"})
        await instance.save()
        return instance

    @classmethod
    async def authenticate(cls, user_id: int, code: str) -> bool:
        seeds = cls.objects().where(
            cls.user_id == user_id,
            cls.revoked_at.is_null(),
        )

        # We check all seeds - a user is allowed multiple seeds (i.e. if they
        # have multiple devices).

        for seed in seeds:
            # TODO - add the proper code checking
            if seed.code == "abc123":
                seed.last_used_at = datetime.datetime.now(
                    tz=datetime.timezone.utc
                )
                await seed.save(columns=[cls.last_used_at])

                return True

        return False
