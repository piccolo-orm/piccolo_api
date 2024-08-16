from abc import ABCMeta, abstractmethod

from piccolo.apps.user.tables import BaseUser


class MFAProvider(metaclass=ABCMeta):

    def __init__(self, token_name: str = "mfa_code"):
        """
        This is the base class which all providers must inherit from. Use it
        to build your own custom providers. If you use it directly, it won't
        do anything. See :class:`AuthenticatorProvider <piccolo_api.mfa.provider.AuthenticatorProvider>`
        for a concrete implementation.

        :param token_name:
            Each provider should specify a unique ``token_name``, so
            when a token is passed to the login endpoint, we know which
            ``MFAProvider`` it belongs to.

        """  # noqa: E501
        self.token_name = token_name

    @abstractmethod
    async def authenticate_user(self, user: BaseUser, code: str) -> bool:
        """
        Should return ``True`` if the code is correct for the user.

        The code could be a TOTP code, or a recovery code.

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

    @abstractmethod
    async def delete_registration(self, user: BaseUser):
        """
        Used to remove the MFA.
        """
        pass
