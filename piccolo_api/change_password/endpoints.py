from __future__ import annotations

import os
import typing as t
from abc import ABCMeta, abstractproperty
from json import JSONDecodeError

from jinja2 import Environment, FileSystemLoader
from piccolo.apps.user.tables import BaseUser
from starlette.endpoints import HTTPEndpoint, Request
from starlette.exceptions import HTTPException
from starlette.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
)
from starlette.status import HTTP_303_SEE_OTHER

from piccolo_api.session_auth.tables import SessionsBase
from piccolo_api.shared.auth.styles import Styles

if t.TYPE_CHECKING:  # pragma: no cover
    from jinja2 import Template
    from starlette.responses import Response


CHANGE_PASSWORD_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "templates",
    "change_password.html",
)


class ChangePasswordEndpoint(HTTPEndpoint, metaclass=ABCMeta):
    @abstractproperty
    def _auth_table(self) -> t.Type[BaseUser]:
        raise NotImplementedError

    @abstractproperty
    def _change_password_template(self) -> Template:
        raise NotImplementedError

    @abstractproperty
    def _styles(self) -> Styles:
        raise NotImplementedError

    def render_template(
        self, request: Request, template_context: t.Dict[str, t.Any] = {}
    ) -> HTMLResponse:
        # If CSRF middleware is present, we have to include a form field with
        # the CSRF token. It only works if CSRFMiddleware has
        # allow_form_param=True, otherwise it only looks for the token in the
        # header.
        csrftoken = request.scope.get("csrftoken")
        csrf_cookie_name = request.scope.get("csrf_cookie_name")

        return HTMLResponse(
            self._change_password_template.render(
                csrftoken=csrftoken,
                csrf_cookie_name=csrf_cookie_name,
                request=request,
                styles=self._styles,
                **template_context,
            )
        )

    async def get(
        self, request: Request
    ) -> t.Union[HTMLResponse, PlainTextResponse]:
        session_user = (
            await SessionsBase.select(SessionsBase.user_id)
            .where(SessionsBase.token == request.cookies.get("id"))
            .first()
        )
        if session_user:
            return self.render_template(request)
        else:
            return PlainTextResponse("Not authenticated", status_code=401)

    async def post(self, request: Request) -> Response:
        # Some middleware (for example CSRF) has already awaited the request
        # body, and adds it to the request.
        body = request.scope.get("form")

        if not body:
            try:
                body = await request.json()
            except JSONDecodeError:
                body = await request.form()

        old_password = body.get("old_password", None)
        new_password = body.get("new_password", None)
        confirm_password = body.get("confirm_password", None)

        if (not old_password) or (not new_password) or (not confirm_password):
            raise HTTPException(
                status_code=401,
                detail="Form is invalid. Missing one or more fields.",
            )

        if len(new_password) < 6:
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={
                        "error": "Password must be at least 6 characters long."
                    },
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Password must be at least 6 characters long.",
                )

        if confirm_password != new_password:
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={"error": "Passwords do not match."},
                )
            else:
                raise HTTPException(
                    status_code=401, detail="Passwords do not match."
                )

        session_user = (
            await SessionsBase.select(SessionsBase.user_id)
            .where(SessionsBase.token == request.cookies.get("id"))
            .first()
        )

        await self._auth_table.update_password(
            user=session_user["user_id"], password=new_password
        )

        # after password changes we invalidate session and redirect user
        # to login endpoint to login again with new password
        response = RedirectResponse(
            url="/login/", status_code=HTTP_303_SEE_OTHER
        )
        response.delete_cookie("id")
        return response


def change_password(
    auth_table: t.Optional[t.Type[BaseUser]] = None,
    template_path: t.Optional[str] = None,
    styles: t.Optional[Styles] = None,
) -> t.Type[ChangePasswordEndpoint]:
    """
    An endpoint for changing passwords.

    :param auth_table:
        Which ``Table`` to create the user in. If not specified,
        it defaults to :class:`BaseUser <piccolo.apps.user.tables.BaseUser>`.
    :param template_path:
        If you want to override the default change password HTML template,
        you can do so by specifying the absolute path to a custom template.
        For example ``'/some_directory/change_password.html'``. Refer to
        the default template at ``piccolo_api/templates/change_password.html``
        as a basis for your custom template.
    :param styles:
        Modify the appearance of the HTML template using CSS.

    """
    template_path = (
        CHANGE_PASSWORD_TEMPLATE_PATH
        if template_path is None
        else template_path
    )

    directory, filename = os.path.split(template_path)
    environment = Environment(loader=FileSystemLoader(directory))
    change_password_template = environment.get_template(filename)

    class _ChangePasswordEndpoint(ChangePasswordEndpoint):
        _auth_table = auth_table or BaseUser
        _change_password_template = change_password_template
        _styles = styles or Styles()

    return _ChangePasswordEndpoint
