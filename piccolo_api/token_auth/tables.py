import uuid

from asgiref.sync import async_to_sync

from piccolo.columns.column_types import Varchar, ForeignKey
from piccolo.extensions.user.tables import BaseUser
from piccolo.table import Table


class TokenAuth(Table):
    """
    Holds randomly generated tokens.

    Useful for mobile authentication, IOT etc. Session auth is recommended for
    web usage.
    """

    token = Varchar(default=uuid.uuid4)
    user = ForeignKey(references=BaseUser)

    @classmethod
    async def create_token(cls, user_id: int) -> str:
        token_auth = await cls(user=user_id).save().run()
        return token_auth.token

    @classmethod
    def create_token_sync(cls, user_id: int) -> str:
        return async_to_sync(cls.create_token)(user_id)
