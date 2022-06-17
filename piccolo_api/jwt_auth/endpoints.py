from __future__ import annotations

import typing as t
from abc import abstractproperty
from datetime import datetime, timedelta

import jwt
from piccolo.apps.user.tables import BaseUser
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse


class JWTLoginBase(HTTPEndpoint):
    @abstractproperty
    def _auth_table(self) -> t.Type[BaseUser]:
        raise NotImplementedError

    @abstractproperty
    def _secret(self) -> str:
        raise NotImplementedError

    @abstractproperty
    def _expiry(self) -> timedelta:
        raise NotImplementedError

    async def post(self, request: Request) -> JSONResponse:
        body = await request.json()
        username = body.get("username", None)
        password = body.get("password", None)

        user_id = await self._auth_table.login(
            username=username, password=password
        )

        if not user_id:
            raise HTTPException(status_code=401, detail="Login failed")

        expiry = datetime.now() + self._expiry

        payload = jwt.encode({"user_id": user_id, "exp": expiry}, self._secret)

        return JSONResponse({"token": payload})


def jwt_login(
    secret: str,
    auth_table: t.Type[BaseUser] = BaseUser,
    expiry: timedelta = timedelta(days=1),
) -> t.Type[JWTLoginBase]:
    """
    Create an endpoint for generating JWT tokens.

    :param secret:
        Used to sign the the JWT tokens.
    :param auth_table:
        Which Piccolo table to use to authenticate the user.
    :param expiry:
        How long before the JWT token expires.

    """

    class JWTLogin(JWTLoginBase):
        _auth_table = auth_table
        _secret = secret
        _expiry = expiry

    return JWTLogin
