from __future__ import annotations

from datetime import timedelta
import typing as t

from piccolo.apps.user.tables import BaseUser as PiccoloBaseUser
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
    """
    Inspects a cookie for a session token, and looks for a user with a matching
    session in the database.
    """

    def __init__(
        self,
        auth_table: t.Type[PiccoloBaseUser] = PiccoloBaseUser,
        session_table: t.Type[SessionsBase] = SessionsBase,
        cookie_name: str = "id",
        admin_only: bool = True,
        superuser_only: bool = False,
        active_only: bool = True,
        increase_expiry: t.Optional[timedelta] = None,
    ):
        """
        :param auth_table:
            The Piccolo table used for authenticating users.
        :param session_table:
            The Piccolo table used for storing sessions.
        :param cookie_name:
            The name of the session cookie. Override this if it clashes with
            other cookies in your application.
        :param admin_only:
            If True, users which aren't admins will be rejected.
        :param superuser_only:
            If True, users which aren't superusers will be rejected.
        :param active_only:
            If True, users which aren't active will be rejected.
        :param increase_expiry:
            If set, the session expiry will be increased by this amount on each
            request, if it's close to expiry. This allows sessions to have a
            short expiry date, whilst also providing a good user experience.
        """
        super().__init__()
        self.auth_table = auth_table
        self.session_table = session_table
        self.cookie_name = cookie_name
        self.admin_only = admin_only
        self.superuser_only = superuser_only
        self.active_only = active_only
        self.increase_expiry = increase_expiry

    async def authenticate(
        self, conn: HTTPConnection
    ) -> t.Optional[t.Tuple[AuthCredentials, BaseUser]]:
        token = conn.cookies.get(self.cookie_name, None)
        if not token:
            raise AuthenticationError()

        user_id = await self.session_table.get_user_id(
            token, increase_expiry=self.increase_expiry
        )

        if not user_id:
            raise AuthenticationError()

        piccolo_user = (
            await self.auth_table.objects()
            .where(self.auth_table.id == user_id)
            .first()
            .run()
        )

        if not piccolo_user:
            raise AuthenticationError("That user doesn't exist anymore")

        if self.admin_only and not piccolo_user.admin:
            raise AuthenticationError("Admin users only")

        if self.superuser_only and not piccolo_user.superuser:
            raise AuthenticationError("Superusers only")

        if self.active_only and not piccolo_user.active:
            raise AuthenticationError("Active users only")

        user = User(
            auth_table=self.auth_table,
            user_id=piccolo_user.id,
            username=piccolo_user.username,
        )

        return (AuthCredentials(scopes=["authenticated"]), user)
