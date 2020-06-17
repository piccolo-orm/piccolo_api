from __future__ import annotations
from abc import abstractmethod, ABCMeta
import typing as t

from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse, Response
from starlette.requests import Request
from piccolo.apps.user.tables import BaseUser

from .tables import TokenAuth


class TokenProvider(metaclass=ABCMeta):
    """
    Subclass this to provide your own custom token provider.
    """

    @abstractmethod
    async def get_token(self, username: str, password: str) -> t.Optional[str]:
        pass


class PiccoloTokenProvider(TokenProvider):
    """
    Retrieves a token from a Piccolo table.
    """

    async def get_token(self, username: str, password: str) -> t.Optional[str]:
        user = await BaseUser.login(username=username, password=password)

        if user:
            response = (
                await TokenAuth.select(TokenAuth.token)
                .first()
                .where(TokenAuth.user == user)
                .run()
            )
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
                    content="The credentials were incorrect", status_code=401,
                )
        else:
            return Response(
                content="No credentials were found.", status_code=401
            )
