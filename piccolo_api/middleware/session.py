from __future__ import annotations

import typing as t

from piccolo.extensions.user import BaseUser as PiccoloBaseUser
from piccolo_api.tables.sessions import SessionsBase
from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    BaseUser,
)
from starlette.requests import HTTPConnection


class User(BaseUser):
    def __init__(self, auth_table: PiccoloBaseUser, user_id: int):
        super().__init__()
        self.auth_table = auth_table
        self.user_id = user_id

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return ""

    @property
    def identity(self) -> str:
        return ""


class SessionsAuthBackend(AuthenticationBackend):
    def __init__(
        self, auth_table: PiccoloBaseUser, session_table: SessionsBase
    ):
        super().__init__()
        self.auth_table = auth_table
        self.session_table = session_table

    async def authenticate(
        self, conn: HTTPConnection
    ) -> t.Optional[t.Tuple[AuthCredentials, BaseUser]]:
        token = conn.cookies.get("id", None)
        if not token:
            return None

        user_id = await self.session_table.get_user_id(token)

        if not user_id:
            return None

        user = User(auth_table=self.auth_table, user_id=user_id)

        return (AuthCredentials(scopes=["authenticated"]), user)
