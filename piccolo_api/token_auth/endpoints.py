from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional

from piccolo.apps.user.tables import BaseUser
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_401_UNAUTHORIZED

from .tables import TokenAuth


class TokenProvider(metaclass=ABCMeta):
    """
    Subclass this to provide your own custom token provider.
    """

    @abstractmethod
    async def get_token(self, username: str, password: str) -> Optional[str]:
        pass


class PiccoloTokenProvider(TokenProvider):
    """
    Retrieves a token from a Piccolo table.
    """

    async def get_token(self, username: str, password: str) -> Optional[str]:
        user = await BaseUser.login(username=username, password=password)

        if user:
            response = (
                await TokenAuth.select(TokenAuth.token)
                .where(TokenAuth.user == user)
                .first()
            )
            if response:
                return response["token"]

        return None


class TokenAuthLoginEndpoint(HTTPEndpoint):
    token_provider: TokenProvider = PiccoloTokenProvider()

    async def post(self, request: Request) -> Response:
        """
        Return a token if the credentials are correct.
        """
        json = await request.json()
        username = json.get("username")
        password = json.get("password")

        if username and password:
            token = await self.token_provider.get_token(
                username=username, password=password
            )
            if token:
                return JSONResponse({"token": str(token)})
            else:
                return Response(
                    content="The credentials were incorrect",
                    status_code=HTTP_401_UNAUTHORIZED,
                )
        else:
            return Response(
                content="No credentials were found.",
                status_code=HTTP_401_UNAUTHORIZED,
            )


def token_login(
    provider: TokenProvider = PiccoloTokenProvider(),
) -> type[TokenAuthLoginEndpoint]:
    """
    Create an endpoint for logging using tokens.

    :param token_provider:
        Used to check if a token is valid.

    """

    class TokenAuthLoginEndpoint_(TokenAuthLoginEndpoint):
        token_provider = provider

    return TokenAuthLoginEndpoint_
