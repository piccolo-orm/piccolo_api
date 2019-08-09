import typing as t

from starlette.exceptions import HTTPException
import jwt

from piccolo.extensions.user import BaseUser


class JWTBlacklist():

    async def in_blacklist(self, token: str) -> bool:
        """
        Checks whether the token is in the blacklist.
        """
        return False


class JWTMiddleware():
    """
    Protects an endpoint - only allows access if a JWT token is presented.
    """
    auth_table: BaseUser = None

    def __init__(
        self,
        asgi,
        auth_table: BaseUser,
        secret: str,
        blacklist: JWTBlacklist = JWTBlacklist()
    ) -> None:
        self.asgi = asgi
        self.secret = secret
        self.auth_table = auth_table
        self.blacklist = blacklist

    def get_token(self, headers: dict) -> t.Optional[str]:
        """
        Try and extract the JWT token from the request headers.
        """
        auth_token = headers.get(b'authorization', None)
        if not auth_token:
            return None
        auth_str = auth_token.decode()
        if not auth_str.startswith('Bearer '):
            return None
        return auth_str.split(' ')[1]

    async def get_user_id(self, token: str) -> t.Optional[int]:
        """
        Extract the user_id from the token, and check it's valid.
        """
        message = jwt.decode(token, self.secret)
        user_id = message.get('user_id', None)

        if not user_id:
            return None

        exists = await self.auth_table.exists().where(
            self.auth_table.id == user_id
        ).run()

        if exists == True:
            return user_id
        else:
            return None

    async def __call__(self, scope, receive, send):
        """
        Add the user_id to the scope if a JWT token is available, and the user
        is recognised, otherwise raise a 403 HTTP error.
        """
        headers = dict(scope['headers'])
        token = self.get_token(headers)
        if not token:
            raise HTTPException(status_code=403)

        if await self.blacklist.in_blacklist(token):
            raise HTTPException(status_code=403)

        user_id = await self.get_user_id(token)
        if not user_id:
            raise HTTPException(status_code=403)

        scope['user_id'] = user_id

        await self.asgi(scope, receive, send)
