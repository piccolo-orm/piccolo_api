from __future__ import annotations
from abc import abstractproperty
from datetime import datetime, timedelta
import typing as t

import jwt
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.requests import Request

from piccolo.apps.user.tables import BaseUser


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
    class JWTLogin(JWTLoginBase):
        _auth_table = auth_table
        _secret = secret
        _expiry = expiry

    return JWTLogin
