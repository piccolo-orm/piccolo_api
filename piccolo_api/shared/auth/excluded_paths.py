from __future__ import annotations

import functools
import typing as t

from starlette.authentication import AuthCredentials, AuthenticationBackend
from starlette.requests import HTTPConnection

from piccolo_api.shared.auth import UnauthenticatedUser


def check_excluded_paths(authenticate_func: t.Callable):

    @functools.wraps(authenticate_func)
    async def authenticate(self: AuthenticationBackend, conn: HTTPConnection):
        conn_path = dict(conn)

        excluded_paths = getattr(self, "excluded_paths", None)

        if excluded_paths is None:
            raise ValueError("excluded_paths isn't defined")

        for excluded_path in excluded_paths:
            if excluded_path.endswith("*"):
                if (
                    conn_path["raw_path"]
                    .decode("utf-8")
                    .startswith(excluded_path.rstrip("*"))
                ):
                    return (
                        AuthCredentials(scopes=[]),
                        UnauthenticatedUser(),
                    )
            else:
                if conn_path["path"] == excluded_path:
                    return (
                        AuthCredentials(scopes=[]),
                        UnauthenticatedUser(),
                    )

        return await authenticate_func(self=self, conn=conn)

    return authenticate
