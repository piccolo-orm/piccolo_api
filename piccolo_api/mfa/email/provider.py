from piccolo_api.mfa.provider import MFAProvider

from .tables import EmailCode


class EmailProvider(MFAProvider):
    async def authenticate(self, email: str):
        return await EmailCode.create_new(email=email)
