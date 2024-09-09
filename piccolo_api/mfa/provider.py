from abc import ABCMeta, abstractmethod

from piccolo.apps.user.tables import BaseUser


class MFAProvider(metaclass=ABCMeta):

    def __init__(self, name: str = "MFA Code"):
        """
        This is the base class which all providers must inherit from. Use it
        to build your own custom providers. If you use it directly, it won't
        do anything. See :class:`AuthenticatorProvider <piccolo_api.mfa.authenticator.provider.AuthenticatorProvider>`
        for a concrete implementation.

        :param token_name:
            Each provider should specify a unique ``token_name``, so
            when a token is passed to the login endpoint, we know which
            ``MFAProvider`` it belongs to.

        """  # noqa: E501
        self.name = name

    @abstractmethod
    async def authenticate_user(self, user: BaseUser, code: str) -> bool:
        """
        Should return ``True`` if the code is correct for the user.

        The code could be a TOTP code, or a recovery code.

        """

    @abstractmethod
    async def is_user_enrolled(self, user: BaseUser) -> bool:
        """
        Should return ``True`` if the user is enrolled in this MFA, and hence
        should submit a code.
        """

    @abstractmethod
    async def send_code(self, user: BaseUser) -> bool:
        """
        If the provider needs to send a code (e.g. if using email or SMS), then
        implement it here.

        Return ``True`` if a code was sent, and ``False`` if not (e.g. an app
        based TOTP codes).

        """

    ###########################################################################
    # Registration

    @abstractmethod
    async def get_registration_html(self, user: BaseUser) -> str:
        """
        When a user wants to register for MFA, this HTML is shown containing
        instructions.
        """

    @abstractmethod
    async def get_registration_json(self, user: BaseUser) -> dict:
        """
        When a user wants to register for MFA, the client can request a JSON
        response, rather than HTML, if they want to render the UI themselves.
        """

    @abstractmethod
    async def delete_registration(self, user: BaseUser):
        """
        Used to remove the MFA.
        """
