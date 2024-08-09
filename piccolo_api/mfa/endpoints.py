from abc import ABCMeta, abstractmethod

from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from piccolo_api.mfa.provider import MFAProvider


class MFARegisterEndpoint(HTTPEndpoint, metaclass=ABCMeta):

    @property
    @abstractmethod
    def _provider(self) -> MFAProvider:
        raise NotImplementedError

    async def get(self, request: Request):
        if request.query_params.get("format") == "json":
            return HTMLResponse(content=self._provider.get_registration_html())
        else:
            return JSONResponse(content=self._provider.get_registration_json())

    async def post(self, request: Request):
        # TODO - we might need the user to confirm once they're setup.
        # We could embed the ID of the row in the HTML response (in a form).
        pass


def mfa_register_endpoint(provider: MFAProvider) -> HTTPEndpoint:

    class _MFARegisterEndpoint(MFARegisterEndpoint):
        _provider = provider

    return _MFARegisterEndpoint
