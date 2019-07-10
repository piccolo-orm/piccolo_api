import jwt
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.requests import Request

from piccolo.extensions.user import BaseUser
import settings


# TODO - accept auth_table and secret
class JWTLogin(HTTPEndpoint):

    async def post(self, request: Request):
        body = await request.json()
        username = body.get('username', None)
        password = body.get('password', None)

        user_id = await BaseUser.login(username=username, password=password)

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Login failed"
            )

        payload = jwt.encode({'user_id': user_id}, settings.SECRET)

        return JSONResponse(payload)
