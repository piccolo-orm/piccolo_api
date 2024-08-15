import os
import typing as t
from abc import ABCMeta, abstractmethod
from json import JSONDecodeError

from jinja2 import Environment, FileSystemLoader
from piccolo.apps.user.tables import BaseUser
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from piccolo_api.mfa.provider import MFAProvider
from piccolo_api.shared.auth.styles import Styles

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "templates",
)


environment = Environment(
    loader=FileSystemLoader(TEMPLATE_PATH), autoescape=True
)


class MFARegisterEndpoint(HTTPEndpoint, metaclass=ABCMeta):

    @property
    @abstractmethod
    def _provider(self) -> MFAProvider:
        raise NotImplementedError

    @property
    @abstractmethod
    def _auth_table(self) -> t.Type[BaseUser]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _styles(self) -> Styles:
        raise NotImplementedError

    def _render_register_template(
        self,
        request: Request,
        extra_context: t.Optional[t.Dict] = None,
        status_code: int = 200,
    ):
        template = environment.get_template("mfa_register.html")

        return HTMLResponse(
            status_code=status_code,
            content=template.render(
                styles=self._styles,
                csrftoken=request.scope.get("csrftoken"),
                **(extra_context or {}),
            ),
        )

    async def get(self, request: Request):
        return self._render_register_template(request=request)

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
                password = body.get("password")

                if not password or not await self._auth_table.login(
                    username=piccolo_user.username, password=password
                ):
                    return self._render_register_template(
                        request=request,
                        status_code=403,
                        extra_context={"error": "Incorrect password"},
                    )

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


def mfa_register_endpoint(
    provider: MFAProvider,
    auth_table: t.Type[BaseUser] = BaseUser,
    styles: t.Optional[Styles] = None,
) -> t.Type[HTTPEndpoint]:

    class _MFARegisterEndpoint(MFARegisterEndpoint):
        _auth_table = auth_table
        _provider = provider
        _styles = styles or Styles()

    return _MFARegisterEndpoint
