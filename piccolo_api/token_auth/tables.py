from __future__ import annotations

import uuid
from typing import Optional, cast

from piccolo.apps.user.tables import BaseUser
from piccolo.columns.column_types import ForeignKey, Serial, Varchar
from piccolo.table import Table
from piccolo.utils.sync import run_sync


def generate_token() -> str:
    return str(uuid.uuid4())


class TokenAuth(Table):
    """
    Holds randomly generated tokens.

    Useful for mobile authentication, IOT etc. Session auth is recommended for
    web usage.
    """

    id: Serial
    token = Varchar(default=generate_token)
    user = ForeignKey(references=BaseUser)

    @classmethod
    async def create_token(
        cls, user_id: int, one_per_user: bool = True
    ) -> str:
        """
        Create a new token.

        :param one_per_user:
            If True, a ValueError is raised if a token already exists for that
            user.

        """
        if (
            await cls.exists().where(cls.user.id == user_id).run()
            and one_per_user
        ):
            raise ValueError(f"User {user_id} already has a token.")

        token_auth = cls(user=user_id)
        await token_auth.save().run()

        return cast(str, token_auth.token)

    @classmethod
    def create_token_sync(cls, user_id: int) -> str:
        return run_sync(cls.create_token(user_id))

    @classmethod
    async def authenticate(cls, token: str) -> Optional[dict]:
        return await cls.select(cls.user).where(cls.token == token).first()

    @classmethod
    def authenticate_sync(cls, token: str) -> Optional[dict]:
        return run_sync(cls.authenticate(token))

    @classmethod
    async def get_user_id(cls, token: str) -> Optional[int]:
        """
        Returns the user_id if the given token is valid, otherwise None.
        """
        data = await cls.authenticate(token=token)
        return data.get("user", None) if data else None
