from collections.abc import Sequence
from typing import Optional

from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
)
from starlette.requests import HTTPConnection


class AuthenticationBackendJunction(AuthenticationBackend):
    """
    Use when you want several different authentication backends to protect
    the same endpoint - if any of them pass, then auth is successful.
    """

    def __init__(self, backends: Sequence[AuthenticationBackend]):
        self.backends = backends

    async def authenticate(
        self, conn: HTTPConnection
    ) -> Optional[tuple[AuthCredentials, BaseUser]]:
        for backend in self.backends:
            try:
                response = await backend.authenticate(conn=conn)
            except AuthenticationError:
                pass
            else:
                return response

        raise AuthenticationError("Auth failed on all backends.")
