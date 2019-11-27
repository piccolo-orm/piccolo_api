from __future__ import annotations

from abc import abstractmethod, ABCMeta
import typing as t

from piccolo.extensions.user.tables import BaseUser
from piccolo_api.token_auth.tables import TokenAuth
from piccolo_api.shared.auth import User
from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    AuthenticationError,
)
from starlette.requests import HTTPConnection


class TokenAuthProvider(metaclass=ABCMeta):
    """
    Subclass to create your own token provider.
    """

    @abstractmethod
    async def get_user(self, token: str) -> User:
        pass


class PiccoloTokenAuthProvider(TokenAuthProvider):
    def __init__(
        self,
        auth_table: BaseUser = BaseUser,
        token_table: TokenAuth = TokenAuth,
    ):
        self.auth_table = auth_table
        self.token_table = token_table

    async def get_user(self, token: str) -> User:
        user_id = await self.token_table.get_user_id(token)

        if not user_id:
            raise AuthenticationError()

        username = (
            await self.auth_table.select(self.auth_table.username)
            .where(self.auth_table.id == user_id)
            .first()
            .run()
        )["username"]

        user = User(
            auth_table=self.auth_table, user_id=user_id, username=username
        )
        return user


DEFAULT_PROVIDER = PiccoloTokenAuthProvider()


class TokenAuthBackend(AuthenticationBackend):
    def __init__(
        self, token_auth_provider: TokenAuthProvider = DEFAULT_PROVIDER,
    ):
        super().__init__()
        self.token_auth_provider = token_auth_provider

    def extract_token(self, header: str) -> str:
        try:
            token = header.split("Bearer ")[1]
        except IndexError:
            raise AuthenticationError("Header is in the wrong format.")

        return token

    async def authenticate(
        self, conn: HTTPConnection
    ) -> t.Optional[t.Tuple[AuthCredentials, BaseUser]]:

        auth_header = conn.headers.get("authentication")
        token = self.extract_token(auth_header)

        user = await self.token_auth_provider.get_user(token=token)

        return (AuthCredentials(scopes=["authenticated"]), user)
