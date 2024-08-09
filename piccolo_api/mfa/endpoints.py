import typing as t
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
        piccolo_user = request.user.user

        if request.query_params.get("format") == "json":
            json_content = await self._provider.get_registration_json(
                user=piccolo_user
            )
            return JSONResponse(content=json_content)
        else:
            html_content = await self._provider.get_registration_html(
                user=piccolo_user
            )
            return HTMLResponse(content=html_content)

    async def post(self, request: Request):
        # TODO - we might need the user to confirm once they're setup.
        # We could embed the ID of the row in the HTML response (in a form).
        pass


def mfa_register_endpoint(provider: MFAProvider) -> t.Type[HTTPEndpoint]:

    class _MFARegisterEndpoint(MFARegisterEndpoint):
        _provider = provider

    return _MFARegisterEndpoint
