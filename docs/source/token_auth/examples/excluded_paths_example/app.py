"""
An example usage of excluded_paths.
"""

from fastapi import Depends, FastAPI
from fastapi.middleware import Middleware
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.authentication import AuthenticationMiddleware
from tables import Movie  # An example Table

from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIKwargs, FastAPIWrapper
from piccolo_api.token_auth.middleware import (
    SecretTokenAuthProvider,
    TokenAuthBackend,
)

app = FastAPI(
    dependencies=[Depends(APIKeyHeader(name="Authorization"))],
    middleware=[
        Middleware(
            AuthenticationMiddleware,
            backend=TokenAuthBackend(
                SecretTokenAuthProvider(tokens=["abc123"]),
                excluded_paths=["/docs", "/openapi.json"],
            ),
        )
    ],
)


# This is a quick way of building FastAPI endpoiints using Piccolo, but isn't
# required:
FastAPIWrapper(
    "/movies/",
    fastapi_app=app,
    piccolo_crud=PiccoloCRUD(Movie, read_only=False),
    fastapi_kwargs=FastAPIKwargs(
        all_routes={"tags": ["Movie"]},
    ),
)
