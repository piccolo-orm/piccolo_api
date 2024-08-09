from abc import ABCMeta, abstractmethod

from piccolo.apps.user.tables import BaseUser


class MFAProvider(metaclass=ABCMeta):

    @abstractmethod
    async def authenticate_user(self, user: BaseUser, code: str) -> bool:
        """
        Should return ``True`` if the code is correct for the user.
        """
        pass

    @abstractmethod
    async def is_user_enrolled(self, user: BaseUser) -> bool:
        """
        Should return ``True`` if the user is enrolled in this MFA, and hence
        should submit a code.
        """
        pass

    @abstractmethod
    async def send_code(self, user: BaseUser):
        """
        If the provider needs to send a code (e.g. if using email or SMS), then
        implement it here. For app based TOTP codes, this can be a NO-OP.
        """
        pass

    ###########################################################################
    # Registration

    @abstractmethod
    async def get_registration_html(self, user: BaseUser) -> str:
        """
        When a user wants to register for MFA, this HTML is shown containing
        instructions.
        """
        pass

    @abstractmethod
    async def get_registration_json(self, user: BaseUser) -> dict:
        """
        When a user wants to register for MFA, the client can request a JSON
        response, rather than HTML, if they want to render the UI themselves.
        """
        pass
