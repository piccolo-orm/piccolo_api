from __future__ import annotations

import typing as t
from abc import ABCMeta, abstractmethod

from piccolo.apps.user.tables import BaseUser as BaseUserTable
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
    SimpleUser,
)
from starlette.requests import HTTPConnection

from piccolo_api.shared.auth import UnauthenticatedUser, User
from piccolo_api.token_auth.tables import TokenAuth


class TokenAuthProvider(metaclass=ABCMeta):
    """
    Subclass to create your own token provider.
    """

    @abstractmethod
    async def get_user(self, token: str) -> BaseUser:
        pass


class SecretTokenAuthProvider(TokenAuthProvider):
    """
    Checks that the token belongs to a predefined list of tokens. This is
    useful for very simple authentication use cases - such as internal
    microservices, where the client is trusted.
    """

    def __init__(self, tokens: t.Sequence[str]):
        self.tokens = tokens

    async def get_user(self, token: str) -> SimpleUser:
        if token in self.tokens:
            user = SimpleUser(username="secret_token_user")
            return user

        raise AuthenticationError("Token not recognised")


class PiccoloTokenAuthProvider(TokenAuthProvider):
    """
    Use this when the token is stored in a Piccolo database table.
    """

    def __init__(
        self,
        auth_table: t.Type[BaseUserTable] = BaseUserTable,
        token_table: t.Type[TokenAuth] = TokenAuth,
    ):
        self.auth_table = auth_table
        self.token_table = token_table

    async def get_user(self, token: str) -> User:
        user_id = await self.token_table.get_user_id(token)

        if not user_id:
            raise AuthenticationError()

        user = (
            await self.auth_table.objects()
            .where(self.auth_table._meta.primary_key == user_id)
            .first()
            .run()
        )

        if user is None:
            raise AuthenticationError()

        return User(user=user)


DEFAULT_PROVIDER = PiccoloTokenAuthProvider()


class TokenAuthBackend(AuthenticationBackend):
    def __init__(
        self,
        token_auth_provider: TokenAuthProvider = DEFAULT_PROVIDER,
        excluded_paths: t.Optional[t.Sequence[str]] = None,
    ):
        """
        :param token_auth_provider:
            Used to verify that a token is correct.
        :param excluded_paths:
            These paths don't require a token.
        """
        super().__init__()
        self.token_auth_provider = token_auth_provider
        self.excluded_paths = excluded_paths or []

    def extract_token(self, header: str) -> str:
        try:
            token = header.split("Bearer ")[1]
        except IndexError:
            raise AuthenticationError("The header is in the wrong format.")

        return token

    async def authenticate(
        self, conn: HTTPConnection
    ) -> t.Optional[t.Tuple[AuthCredentials, BaseUser]]:
        auth_header = conn.headers.get("Authorization", None)
        conn_path = dict(conn)

        for excluded_path in self.excluded_paths:
            if excluded_path.endswith("*"):
                if (
                    conn_path["raw_path"]
                    .decode("utf-8")
                    .startswith(excluded_path.rstrip("*"))
                ):
                    return (
                        AuthCredentials(scopes=[]),
                        UnauthenticatedUser(),
                    )
            else:
                if conn_path["path"] == excluded_path:
                    return (
                        AuthCredentials(scopes=[]),
                        UnauthenticatedUser(),
                    )

        if not auth_header:
            raise AuthenticationError("The Authorization header is missing.")

        token = self.extract_token(auth_header)

        user = await self.token_auth_provider.get_user(token=token)

        return (AuthCredentials(scopes=["authenticated"]), user)
