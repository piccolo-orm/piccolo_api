from abc import ABCMeta

from starlette.endpoints import HTTPEndpoint


class MFARegisterEndpoint(HTTPEndpoint, metaclass=ABCMeta):
    pass
