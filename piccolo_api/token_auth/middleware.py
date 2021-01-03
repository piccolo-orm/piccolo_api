from __future__ import annotations

from abc import abstractmethod, ABCMeta
import typing as t

from piccolo.apps.user.tables import BaseUser as BaseUserTable
from piccolo_api.token_auth.tables import TokenAuth
from piccolo_api.shared.auth import User
from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    AuthenticationError,
    SimpleUser,
    BaseUser,
)
from starlette.requests import HTTPConnection


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
        self,
        token_auth_provider: TokenAuthProvider = DEFAULT_PROVIDER,
    ):
        super().__init__()
        self.token_auth_provider = token_auth_provider

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

        if not auth_header:
            raise AuthenticationError("The Authorization header is missing.")

        token = self.extract_token(auth_header)

        user = await self.token_auth_provider.get_user(token=token)

        return (AuthCredentials(scopes=["authenticated"]), user)
