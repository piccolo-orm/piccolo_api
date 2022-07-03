from __future__ import annotations

import os
import typing as t
from abc import ABCMeta, abstractproperty
from json import JSONDecodeError

from jinja2 import Environment, FileSystemLoader
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
    def _login_url(self) -> str:
        raise NotImplementedError

    @abstractproperty
    def _change_password_template(self) -> Template:
        raise NotImplementedError

    @abstractproperty
    def _styles(self) -> Styles:
        raise NotImplementedError

    @abstractproperty
    def _session_table(self) -> t.Optional[t.Type[SessionsBase]]:
        raise NotImplementedError

    @abstractproperty
    def _session_cookie_name(self) -> t.Optional[str]:
        raise NotImplementedError

    @abstractproperty
    def _read_only(self) -> bool:
        raise NotImplementedError

    def render_template(
        self,
        request: Request,
        template_context: t.Dict[str, t.Any] = {},
        login_url: t.Optional[str] = None,
        min_password_length: int = 6,
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
                username=request.user.user.username,
                login_url=login_url,
                min_password_length=min_password_length,
                **template_context,
            )
        )

    async def get(self, request: Request) -> Response:
        piccolo_user = request.user.user
        if piccolo_user:
            min_password_length = piccolo_user._min_password_length
            return self.render_template(
                request, min_password_length=min_password_length
            )
        else:
            return RedirectResponse(self._login_url)

    async def post(self, request: Request) -> Response:
        if self._read_only:
            return PlainTextResponse(
                content="Running in read only mode", status_code=405
            )

        # Some middleware (for example CSRF) has already awaited the request
        # body, and adds it to the request.
        body = request.scope.get("form")

        if not body:
            try:
                body = await request.json()
            except JSONDecodeError:
                body = await request.form()

        current_password = body.get("current_password", None)
        new_password = body.get("new_password", None)
        confirm_new_password = body.get("confirm_new_password", None)

        piccolo_user = request.user.user
        min_password_length = piccolo_user._min_password_length

        if (
            (not current_password)
            or (not new_password)
            or (not confirm_new_password)
        ):
            error = "Form is invalid. Missing one or more fields."
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={"error": error},
                    min_password_length=min_password_length,
                )
            raise HTTPException(status_code=422, detail=error)

        if len(new_password) < min_password_length:
            error = (
                f"Password must be at least {min_password_length} characters "
                "long."
            )
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    min_password_length=min_password_length,
                    template_context={"error": error},
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail=error,
                )

        if confirm_new_password != new_password:
            error = "Passwords do not match."

            if body.get("format") == "html":
                return self.render_template(
                    request,
                    min_password_length=min_password_length,
                    template_context={"error": error},
                )
            else:
                raise HTTPException(status_code=422, detail=error)

        if not await piccolo_user.login(
            username=piccolo_user.username, password=current_password
        ):
            error = "Incorrect password."
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    min_password_length=min_password_length,
                    template_context={"error": error},
                )
            raise HTTPException(detail=error, status_code=422)

        await piccolo_user.update_password(
            user=request.user.user_id, password=new_password
        )

        #######################################################################
        # After the password changes, we invalidate the session and
        # redirect the user to the login endpoint.

        session_table = self._session_table
        if session_table:
            # This will invalidate all of the user's sessions on all devices.
            await session_table.delete().where(
                session_table.user_id == piccolo_user.id
            )

        response = RedirectResponse(
            url=self._login_url, status_code=HTTP_303_SEE_OTHER
        )

        if self._session_cookie_name:
            response.delete_cookie(self._session_cookie_name)

        return response


def change_password(
    login_url: str = "/login/",
    session_table: t.Optional[t.Type[SessionsBase]] = SessionsBase,
    session_cookie_name: t.Optional[str] = "id",
    template_path: t.Optional[str] = None,
    styles: t.Optional[Styles] = None,
    read_only: bool = False,
) -> t.Type[ChangePasswordEndpoint]:
    """
    An endpoint for changing passwords.

    :param login_url:
        Where to redirect the user to after successfully changing their
        password.
    :param session_table:
        If provided, when the password is changed, the sessions for the user
        will be invalidated in the database.
    :param session_cookie_name:
        If provided, when the password is changed, the session cookie with this
        name will be deleted.
    :param template_path:
        If you want to override the default change password HTML template,
        you can do so by specifying the absolute path to a custom template.
        For example ``'/some_directory/change_password.html'``. Refer to
        the default template at ``piccolo_api/templates/change_password.html``
        as a basis for your custom template.
    :param styles:
        Modify the appearance of the HTML template using CSS.
    :read_only:
        If ``True``, the endpoint only responds to GET requests. It's not
        commonly needed, except when running demos.

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
        _login_url = login_url
        _change_password_template = change_password_template
        _styles = styles or Styles()
        _session_table = session_table
        _session_cookie_name = session_cookie_name
        _read_only = read_only

    return _ChangePasswordEndpoint
