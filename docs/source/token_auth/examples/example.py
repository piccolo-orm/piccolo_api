from fastapi import FastAPI
from home.tables import Movie  # An example Table
from piccolo_admin.endpoints import create_admin
from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIKwargs, FastAPIWrapper
from piccolo_api.token_auth.endpoints import TokenAuthLoginEndpoint
from piccolo_api.token_auth.middleware import (
    PiccoloTokenAuthProvider,
    TokenAuthBackend,
)
from piccolo_api.token_auth.tables import TokenAuth
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.routing import Mount, Route

public_app = FastAPI(
    routes=[
        Mount(
            "/admin/",
            create_admin(tables=[Movie, TokenAuth]),
        ),
        Route("/login/", TokenAuthLoginEndpoint),
    ],
)

private_app = FastAPI()

protected_app = AuthenticationMiddleware(
    private_app,
    backend=TokenAuthBackend(PiccoloTokenAuthProvider()),
)

FastAPIWrapper(
    "/movies/",
    fastapi_app=private_app,
    piccolo_crud=PiccoloCRUD(Movie, read_only=False),
    fastapi_kwargs=FastAPIKwargs(
        all_routes={"tags": ["Movie"]},
    ),
)

public_app.mount("/private", protected_app)
