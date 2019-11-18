from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.requests import Request
from piccolo.extensions.user.tables import BaseUser

from .tables import TokenAuth


class TokenAuthLoginEndpoint(HTTPEndpoint):
    async def post(self, request: Request) -> JSONResponse:
        """
        Return a token if the credentials are correct.
        """
        json = await request.json()
        username = json.get("username")
        password = json.get("password")
        if username and password:
            user = await BaseUser.login(username=username, password=password)
            if user:
                token = (
                    TokenAuth.select(TokenAuth.token)
                    .first()
                    .where(TokenAuth.user == user)
                )
                return JSONResponse({"token": token})
            else:
                raise HTTPException(
                    status_code=401, detail="The credentials were incorrect"
                )
        else:
            raise HTTPException(
                status_code=401, detail="No credentials were found."
            )
