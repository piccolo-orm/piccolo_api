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
        admin_only: bool = True,
    ):
        super().__init__()
        self.auth_table = auth_table
        self.session_table = session_table
        self.cookie_name = cookie_name
        self.admin_only = admin_only

    async def authenticate(
        self, conn: HTTPConnection
    ) -> t.Optional[t.Tuple[AuthCredentials, BaseUser]]:
        token = conn.cookies.get(self.cookie_name, None)
        if not token:
            raise AuthenticationError()

        user_id = await self.session_table.get_user_id(token)

        if not user_id:
            raise AuthenticationError()

        piccolo_user = (
            await self.auth_table.objects()
            .where(self.auth_table.id == user_id)
            .first()
            .run()
        )

        if self.admin_only and not piccolo_user.admin:
            raise AuthenticationError("Admin users only")

        user = User(
            auth_table=self.auth_table,
            user_id=piccolo_user.id,
            username=piccolo_user.username,
        )

        return (AuthCredentials(scopes=["authenticated"]), user)
