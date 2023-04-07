from __future__ import annotations

import enum
import typing as t

import jwt
from piccolo.apps.user.tables import BaseUser
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp


class JWTBlacklist:
    """
    Inherit from this class, and override :meth:`in_blacklist`. Used in
    conjunction with :class:`JWTMiddleware`. An example is
    :class:`StaticJWTBlacklist`.
    """

    async def in_blacklist(self, token: str) -> bool:
        """
        Checks whether the token is in the blacklist.
        """
        return False


class StaticJWTBlacklist(JWTBlacklist):
    """
    A simple implementation of :class:`JWTBlacklist <JWTBlacklist>`, which
    rejects a token if it's in the given list.
    """

    def __init__(self, blacklist: t.List[str]):
        self.blacklist = blacklist

    async def in_blacklist(self, token: str) -> bool:
        return token in self.blacklist


def extend_scope(scope: t.Dict, extra: t.Dict) -> t.Dict:
    """
    We copy the scope and extend it with `extra`. It's best to copy the scope
    rather than manipulate it directly.
    """
    new_scope = dict(scope)
    new_scope.update(extra)
    return new_scope


class JWTError(str, enum.Enum):
    """
    This enum contains all of the possible errors which can be returned by
    :class:`JWTMiddleware`. If ``allow_unauthenticated=True`` then these
    errors will be added to the ASGI scope instead under ``jwt_error``.
    """

    token_not_found = "Token not found"
    token_revoked = "Token revoked"
    token_expired = "Token has expired"
    user_not_found = "User not found"
    token_invalid = "Token is invalid"


class JWTMiddleware:
    """
    Protects ASGI endpoints - only allows access if a JWT token is present in
    the ``authorization`` HTTP header.
    """

    def __init__(
        self,
        asgi: ASGIApp,
        secret: str,
        auth_table: t.Type[BaseUser] = BaseUser,
        blacklist: JWTBlacklist = JWTBlacklist(),
        allow_unauthenticated: bool = False,
    ) -> None:
        """
        :param asgi:
            The ASGI app to protect.
        :param secret:
            The secret used to decode the JWT token.
        :param auth_table:
            The Piccolo table containing users - either
            :class:`BaseUser <piccolo.apps.user.tables.BaseUser>` or a
            subclass.
        :param blacklist:
            Any tokens in this list will be rejected.
        :param allow_unauthenticated:
            By default the middleware rejects any requests with an invalid
            token.

        """
        self.asgi = asgi
        self.secret = secret
        self.auth_table = auth_table
        self.blacklist = blacklist
        self.allow_unauthenticated = allow_unauthenticated

    def get_token(self, headers: dict) -> t.Optional[str]:
        """
        Try and extract the JWT token from the request headers.
        """
        auth_token = headers.get(b"authorization", None)
        if not auth_token:
            return None
        auth_str = auth_token.decode()
        if not auth_str.startswith("Bearer "):
            return None
        return auth_str.split(" ")[1]

    async def get_user(
        self, token_dict: t.Dict[str, t.Any]
    ) -> t.Optional[BaseUser]:
        """
        Extract the user_id from the token, and return a matching user.
        """
        user_id = token_dict.get("user_id", None)

        if not user_id:
            return None

        return await self.auth_table.objects().get(
            self.auth_table._meta.primary_key == user_id
        )

    async def __call__(self, scope, receive, send):
        """
        Add the user_id to the scope if a JWT token is available, and the user
        is recognised, otherwise raise a 403 HTTP error.
        """
        allow_unauthenticated = self.allow_unauthenticated

        headers = dict(scope["headers"])
        token = self.get_token(headers)
        if not token:
            error = JWTError.token_not_found.value
            if allow_unauthenticated:
                await self.asgi(
                    extend_scope(scope, {"user_id": None, "jwt_error": error}),
                    receive,
                    send,
                )
                return
            else:
                raise HTTPException(status_code=403, detail=error)

        if await self.blacklist.in_blacklist(token):
            error = JWTError.token_revoked.value
            if allow_unauthenticated:
                await self.asgi(
                    extend_scope(scope, {"user_id": None, "jwt_error": error}),
                    receive,
                    send,
                )
                return
            else:
                raise HTTPException(status_code=403, detail=error)

        try:
            token_dict = jwt.decode(token, self.secret, algorithms=["HS256"])
        except jwt.exceptions.ExpiredSignatureError:
            error = JWTError.token_expired.value
            if allow_unauthenticated:
                await self.asgi(
                    extend_scope(scope, {"user_id": None, "jwt_error": error}),
                    receive,
                    send,
                )
                return
            else:
                raise HTTPException(status_code=403, detail=error)
        except jwt.exceptions.InvalidSignatureError:
            error = JWTError.token_invalid.value
            if allow_unauthenticated:
                await self.asgi(
                    extend_scope(scope, {"user_id": None, "jwt_error": error}),
                    receive,
                    send,
                )
                return
            else:
                raise HTTPException(status_code=403, detail=error)

        user = await self.get_user(token_dict)
        if user is None:
            error = JWTError.user_not_found.value
            if allow_unauthenticated:
                await self.asgi(
                    extend_scope(scope, {"user_id": None, "jwt_error": error}),
                    receive,
                    send,
                )
                return
            else:
                raise HTTPException(status_code=403, detail=error)

        await self.asgi(
            extend_scope(scope, {"user_id": user.id}), receive, send
        )
