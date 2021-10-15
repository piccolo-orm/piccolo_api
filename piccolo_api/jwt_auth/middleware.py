import typing as t

import jwt
from piccolo.apps.user.tables import BaseUser
from starlette.exceptions import HTTPException


class JWTBlacklist:
    async def in_blacklist(self, token: str) -> bool:
        """
        Checks whether the token is in the blacklist.
        """
        return False


class JWTMiddleware:
    """
    Protects an endpoint - only allows access if a JWT token is presented.
    """

    auth_table: t.Type[BaseUser]

    def __init__(
        self,
        asgi,
        secret: str,
        auth_table: t.Type[BaseUser] = BaseUser,
        blacklist: JWTBlacklist = JWTBlacklist(),
    ) -> None:
        self.asgi = asgi
        self.secret = secret
        self.auth_table = auth_table
        self.blacklist = blacklist

    def get_token(self, headers: dict) -> t.Optional[str]:
        """
        Try and extract the JWT token from the request headers.
        """
        auth_token = headers.get(b"authorization", None)
        if not auth_token:
            return None
        auth_str = auth_token.decode()
        if not auth_str.startswith("Bearer "):
            return None
        return auth_str.split(" ")[1]

    async def get_user_id(
        self, token_dict: t.Dict[str, t.Any]
    ) -> t.Optional[int]:
        """
        Extract the user_id from the token, and check it's valid.
        """
        user_id = token_dict.get("user_id", None)

        if not user_id:
            return None

        exists = (
            await self.auth_table.exists()
            .where(self.auth_table._meta.primary_key == user_id)
            .run()
        )

        if exists is True:
            return user_id
        else:
            return None

    async def __call__(self, scope, receive, send):
        """
        Add the user_id to the scope if a JWT token is available, and the user
        is recognised, otherwise raise a 403 HTTP error.
        """
        headers = dict(scope["headers"])
        token = self.get_token(headers)
        if not token:
            raise HTTPException(status_code=403, detail="Token not found")

        if await self.blacklist.in_blacklist(token):
            raise HTTPException(status_code=403, detail="Token revoked")

        try:
            token_dict = jwt.decode(token, self.secret, algorithms=["HS256"])
        except jwt.exceptions.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="Token has expired")

        user_id = await self.get_user_id(token_dict)
        if not user_id:
            raise HTTPException(status_code=403)

        new_scope = dict(scope)
        new_scope["user_id"] = user_id

        await self.asgi(new_scope, receive, send)
