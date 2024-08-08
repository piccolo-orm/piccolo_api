import typing as t

from piccolo.apps.user.tables import BaseUser

from piccolo_api.mfa.provider import MFAProvider

from .tables import AuthenticatorSecret


class AuthenticatorProvider(MFAProvider):

    def __init__(
        self, seed_table: t.Type[AuthenticatorSecret] = AuthenticatorSecret
    ):
        """
        :param seed_table:
            By default, just use the out of the box ``AuthenticatorSecret``
            table - you can specify a subclass instead if you want to override
            certain functionality.

        """
        self.seed_table = seed_table

    async def authenticate(self, user: BaseUser, code: str) -> bool:
        return await self.seed_table.authenticate(user_id=user.id, code=code)