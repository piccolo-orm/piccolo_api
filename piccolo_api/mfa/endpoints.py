import typing as t
from abc import ABCMeta, abstractmethod
from json import JSONDecodeError

from piccolo.apps.user.tables import BaseUser
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
        return HTMLResponse(
            content=f"""
                <form method="post">
                    <input type="hidden" name="action" value="register" />
                    <input type="hidden" name="csrftoken" value="{request.scope['csrftoken']}" />
                    <button>Register</button>
                </form>
            """  # noqa: E501
        )

    async def post(self, request: Request):
        piccolo_user: BaseUser = request.user.user

        # Some middleware (for example CSRF) has already awaited the request
        # body, and adds it to the request.
        body: t.Any = request.scope.get("form")

        if not body:
            try:
                body = await request.json()
            except JSONDecodeError:
                body = await request.form()

        if action := body.get("action"):
            if action == "register":
                if body.get("format") == "json":
                    json_content = await self._provider.get_registration_json(
                        user=piccolo_user
                    )
                    return JSONResponse(content=json_content)
                else:
                    html_content = await self._provider.get_registration_html(
                        user=piccolo_user
                    )
                    return HTMLResponse(content=html_content)
            elif action == "revoke":
                if password := body.get("password"):
                    if await piccolo_user.__class__.login(
                        username=piccolo_user.username, password=password
                    ):
                        html_content = (
                            await self._provider.delete_registration(
                                user=piccolo_user
                            )
                        )
                        return HTMLResponse(content=html_content)

        return HTMLResponse(content="<p>Error</p>")


def mfa_register_endpoint(provider: MFAProvider) -> t.Type[HTTPEndpoint]:

    class _MFARegisterEndpoint(MFARegisterEndpoint):
        _provider = provider

    return _MFARegisterEndpoint
