from abc import abstractproperty
import typing as t

import jwt
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.requests import Request

from piccolo.extensions.user import BaseUser


class JWTLoginBase(HTTPEndpoint):

    @abstractproperty
    def _auth_table(self) -> t.Type[BaseUser]:
        raise NotImplementedError

    @abstractproperty
    def _secret(self) -> str:
        raise NotImplementedError

    async def post(self, request: Request) -> JSONResponse:
        body = await request.json()
        username = body.get('username', None)
        password = body.get('password', None)

        user_id = await self._auth_table.login(
            username=username,
            password=password
        )

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Login failed"
            )

        payload = jwt.encode({'user_id': user_id}, self._secret).decode()

        return JSONResponse({
            'token': payload
        })


def jwt_login(auth_table: BaseUser, secret: str) -> t.Type[JWTLoginBase]:
    class JWTLogin(JWTLoginBase):
        _auth_table = auth_table
        _secret = secret

    return JWTLogin
