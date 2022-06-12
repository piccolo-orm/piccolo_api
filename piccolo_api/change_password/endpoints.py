from __future__ import annotations

import os
import typing as t
from abc import ABCMeta, abstractproperty
from json import JSONDecodeError

from jinja2 import Environment, FileSystemLoader
from starlette.endpoints import HTTPEndpoint, Request
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

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

    def render_template(
        self,
        request: Request,
        template_context: t.Dict[str, t.Any] = {},
        success: bool = False,
        login_url: t.Optional[str] = None,
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
                success=success,
                login_url=login_url,
                **template_context,
            )
        )

    async def get(self, request: Request) -> HTMLResponse:
        if request.user.user:
            return self.render_template(request)
        raise HTTPException(
            detail="No session cookie found.",
            status_code=401,
        )

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

        user = request.user.user
        piccolo_user = user.__class__

        if (not old_password) or (not new_password) or (not confirm_password):
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={
                        "error": "Form is invalid. Missing one or more fields."
                    },
                )
            raise HTTPException(
                status_code=401,
                detail="Form is invalid. Missing one or more fields.",
            )

        if len(new_password) < piccolo_user._min_password_length:
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

        if not await user.login(username=user.username, password=old_password):
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={"error": "Incorrect password."},
                )
            raise HTTPException(detail="Incorrect password.", status_code=401)

        await piccolo_user.update_password(
            user=request.user.user_id, password=new_password
        )

        # after password changes we invalidate session and redirect user
        # to login endpoint to login again with new password
        response = RedirectResponse(
            url=self._login_url, status_code=HTTP_303_SEE_OTHER
        )
        response.delete_cookie("id")

        if body.get("format") == "html":
            return self.render_template(
                request,
                success=True,
                login_url=self._login_url,
            )
        return response


def change_password(
    login_url: str = "/login/",
    template_path: t.Optional[str] = None,
    styles: t.Optional[Styles] = None,
) -> t.Type[ChangePasswordEndpoint]:
    """
    An endpoint for changing passwords.

    :param login_url:
        If you want to override default redirect url you can specify your own.
        For example ``change_password(login_url="my-login-url"``.
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
        _login_url = login_url
        _change_password_template = change_password_template
        _styles = styles or Styles()

    return _ChangePasswordEndpoint
