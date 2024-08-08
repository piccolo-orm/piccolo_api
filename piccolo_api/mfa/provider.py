from abc import ABCMeta, abstractmethod

from piccolo.apps.user.tables import BaseUser


class MFAProvider(metaclass=ABCMeta):

    @abstractmethod
    async def authenticate(self, user: BaseUser) -> bool:
        pass
