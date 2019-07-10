import typing as t

from starlette.exceptions import HTTPException
import jwt

from piccolo.extensions.user import BaseUser


class JWTMiddleware():
    """
    Protects an endpoint - only allows access if a JWT token is presented.
    """
    auth_table: BaseUser = None

    def __init__(self, asgi, auth_table: BaseUser, secret: str) -> None:
        self.asgi = asgi
        self.secret = secret

    def get_token(self, headers: dict) -> t.Optional[str]:
        """
        Try and extract the JWT token from the request headers.
        """
        auth_str = headers.get('Authorization', None)
        if not auth_str:
            return None
        if not auth_str.startswith('Authorization: Bearer '):
            return None
        return auth_str.split(' ')[2]

    def get_user_id(self, token: str) -> t.Optional[int]:
        """
        Extract the user_id from the token, and check it's valid.
        """
        message = jwt.decode(token, self.secret)
        user_id = message.get('user_id', None)

        if not user_id:
            return None

        if not self.auth_table.exists.where(
            self.auth_table.id == user_id
        ):
            return None
        else:
            return user_id

    def __call__(self, scope, receive, send):
        """
        Add the user_id to the scope if a JWT token is available, and the user
        is recognised, otherwise raise a 403 HTTP error.
        """
        headers = dict(scope['headers'])
        token = self.get_token(headers)
        if not token:
            raise HTTPException(status_code=403)

        user_id = self.get_user_id(token)
        if not user_id:
            raise HTTPException(status_code=403)

        scope['user_id'] = user_id

        return self.asgi(scope)
