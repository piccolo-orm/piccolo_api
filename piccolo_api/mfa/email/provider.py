from piccolo.apps.user.tables import BaseUser

from piccolo_api.mfa.provider import MFAProvider

from .tables import EmailCode


class EmailProvider(MFAProvider):

    async def register(self, user: BaseUser):
        return await EmailCode.create_new(email=user.email)

    async def authenticate_user(self, user: BaseUser, code: str) -> bool:
        return await EmailCode.authenticate(email=user.email, code=code)
