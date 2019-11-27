from __future__ import annotations

import typing as t

from piccolo.extensions.user.tables import BaseUser as PiccoloBaseUser
from piccolo_api.session_auth.tables import SessionsBase
from piccolo_api.shared.auth import User
from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    AuthenticationError,
    BaseUser,
)
from starlette.requests import HTTPConnection


class SessionsAuthBackend(AuthenticationBackend):
    def __init__(
        self,
        auth_table: PiccoloBaseUser = PiccoloBaseUser,
        session_table: SessionsBase = SessionsBase,
        cookie_name: str = "id",
    ):
        super().__init__()
        self.auth_table = auth_table
        self.session_table = session_table
        self.cookie_name = cookie_name

    async def authenticate(
        self, conn: HTTPConnection
    ) -> t.Optional[t.Tuple[AuthCredentials, BaseUser]]:
        token = conn.cookies.get(self.cookie_name, None)
        if not token:
            raise AuthenticationError()

        user_id = await self.session_table.get_user_id(token)

        if not user_id:
            raise AuthenticationError()

        username = (
            await self.auth_table.select(self.auth_table.username)
            .first()
            .run()
        )["username"]

        user = User(
            auth_table=self.auth_table, user_id=user_id, username=username
        )

        return (AuthCredentials(scopes=["authenticated"]), user)
