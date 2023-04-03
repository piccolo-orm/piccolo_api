from datetime import timedelta

from fastapi import FastAPI, Request
from home.tables import Movie  # An example Table
from piccolo_admin.endpoints import create_admin
from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIKwargs, FastAPIWrapper
from piccolo_api.jwt_auth.endpoints import jwt_login
from piccolo_api.jwt_auth.middleware import JWTBlacklist, JWTMiddleware
from starlette.routing import Mount, Route

public_app = FastAPI(
    routes=[
        Mount(
            "/admin/",
            create_admin(tables=[Movie]),
        ),
        Route(
            path="/login/",
            endpoint=jwt_login(
                secret="mysecret123",
                expiry=timedelta(minutes=60),  # default is 1 day
            ),
        ),
    ],
)


BLACKLISTED_TOKENS = []


class MyBlacklist(JWTBlacklist):
    async def in_blacklist(self, token: str) -> bool:
        return token in BLACKLISTED_TOKENS


private_app = FastAPI()

protected_app = JWTMiddleware(
    private_app,
    auth_table=BaseUser,
    secret="mysecret123",
    blacklist=MyBlacklist(),
)

FastAPIWrapper(
    "/movies/",
    fastapi_app=private_app,
    piccolo_crud=PiccoloCRUD(Movie, read_only=False),
    fastapi_kwargs=FastAPIKwargs(
        all_routes={"tags": ["Movies"]},
    ),
)

public_app.mount("/private", protected_app)

# This is optional if you want to provide a logout endpoint
# in your application. By adding a token to the token blacklist,
# you are invalidating the token and need to login again to get
# new valid token
@private_app.get("/logout/")
async def logout(request: Request) -> None:
    BLACKLISTED_TOKENS.append(
        request.headers.get("authorization").split(" ")[-1]
    )
