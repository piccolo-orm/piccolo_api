from __future__ import annotations

import os
import re
import typing as t
from abc import ABCMeta, abstractproperty
from json import JSONDecodeError

from jinja2 import Environment, FileSystemLoader
from piccolo.apps.user.tables import BaseUser
from starlette.datastructures import URL
from starlette.endpoints import HTTPEndpoint, Request
from starlette.exceptions import HTTPException
from starlette.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
)
from starlette.status import HTTP_303_SEE_OTHER

from piccolo_api.shared.auth.styles import Styles

if t.TYPE_CHECKING:  # pragma: no cover
    from jinja2 import Template
    from starlette.responses import Response

    from piccolo_api.shared.auth.captcha import Captcha


SIGNUP_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "templates", "register.html"
)


EMAIL_REGEX = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")


class RegisterEndpoint(HTTPEndpoint, metaclass=ABCMeta):
    @abstractproperty
    def _auth_table(self) -> t.Type[BaseUser]:
        raise NotImplementedError

    @abstractproperty
    def _redirect_to(self) -> t.Union[str, URL]:
        """
        Where to redirect to after login is successful.
        """
        raise NotImplementedError

    @abstractproperty
    def _register_template(self) -> Template:
        raise NotImplementedError

    @abstractproperty
    def _user_defaults(self) -> t.Optional[t.Dict[str, t.Any]]:
        raise NotImplementedError

    @abstractproperty
    def _captcha(self) -> t.Optional[Captcha]:
        raise NotImplementedError

    @abstractproperty
    def _styles(self) -> Styles:
        raise NotImplementedError

    @abstractproperty
    def _read_only(self) -> bool:
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
            self._register_template.render(
                csrftoken=csrftoken,
                csrf_cookie_name=csrf_cookie_name,
                request=request,
                captcha=self._captcha,
                styles=self._styles,
                **template_context,
            )
        )

    async def get(self, request: Request) -> HTMLResponse:
        return self.render_template(request)

    async def post(self, request: Request) -> Response:
        if self._read_only:
            return PlainTextResponse(
                content="Running in read only mode.", status_code=405
            )

        # Some middleware (for example CSRF) has already awaited the request
        # body, and adds it to the request.
        body = request.scope.get("form")

        if not body:
            try:
                body = await request.json()
            except JSONDecodeError:
                body = await request.form()

        username = body.get("username", None)
        email = body.get("email", None)
        password = body.get("password", None)
        confirm_password = body.get("confirm_password", None)

        if self._captcha:
            token = body.get(self._captcha.token_field, None)
            response = await self._captcha.validate(token=token)
            if isinstance(response, str):
                return self.render_template(
                    request,
                    template_context={"error": response},
                )

        if (
            (not username)
            or (not email)
            or (not password)
            or (not confirm_password)
        ):
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={
                        "error": "Form is invalid. Missing one or more fields."
                    },
                )
            raise HTTPException(
                status_code=422,
                detail="Form is invalid. Missing one or more fields.",
            )

        if not EMAIL_REGEX.fullmatch(email):
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={"error": "Invalid email address."},
                )
            else:
                raise HTTPException(
                    status_code=422, detail="Invalid email address."
                )

        if len(password) < 6:
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={
                        "error": "Password must be at least 6 characters long."
                    },
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail="Password must be at least 6 characters long.",
                )

        if confirm_password != password:
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={"error": "Passwords do not match."},
                )
            else:
                raise HTTPException(
                    status_code=422, detail="Passwords do not match."
                )

        if await self._auth_table.count().where(
            self._auth_table.email == email,
            self._auth_table.username == username,
        ):
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={
                        "error": "User with email or username already exists."
                    },
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail="User with email or username already exists.",
                )

        extra_params = self._user_defaults or {}

        await self._auth_table.create_user(
            username=username, password=password, email=email, **extra_params
        )

        return RedirectResponse(
            url=self._redirect_to, status_code=HTTP_303_SEE_OTHER
        )


def register(
    auth_table: t.Type[BaseUser] = BaseUser,
    redirect_to: t.Union[str, URL] = "/login/",
    template_path: t.Optional[str] = None,
    user_defaults: t.Optional[t.Dict[str, t.Any]] = None,
    captcha: t.Optional[Captcha] = None,
    styles: t.Optional[Styles] = None,
    read_only: bool = False,
) -> t.Type[RegisterEndpoint]:
    """
    An endpoint for register user.

    :param auth_table:
        Which ``Table`` to create the user in. It defaults to
        :class:`BaseUser <piccolo.apps.user.tables.BaseUser>`.
    :param redirect_to:
        Where to redirect to after successful registration.
    :param template_path:
        If you want to override the default register HTML template, you can do
        so by specifying the absolute path to a custom template. For example
        ``'/some_directory/register.html'``. Refer to the default template at
        ``piccolo_api/templates/register.html`` as a basis for
        your custom template.
    :param user_defaults:
        These values are assigned to the new user. An example use case is
        setting ``active = True`` on each new user, so they can immediately
        login (not recommended for production, as it's better to verify their
        email address first, but OK for a prototype app)::

            register(user_defaults={'active': True})
    :param captcha:
        Integrate a CAPTCHA service, to provide protection against bots.
        See :class:`Captcha <piccolo_api.shared.auth.captcha.Captcha>`.
    :param styles:
        Modify the appearance of the HTML template using CSS.
    :read_only:
        If ``True``, the endpoint only responds to GET requests. It's not
        commonly needed, except when running demos.

    """
    template_path = (
        SIGNUP_TEMPLATE_PATH if template_path is None else template_path
    )

    directory, filename = os.path.split(template_path)
    environment = Environment(loader=FileSystemLoader(directory))
    register_template = environment.get_template(filename)

    class _RegisterEndpoint(RegisterEndpoint):
        _auth_table = auth_table or BaseUser
        _redirect_to = redirect_to
        _register_template = register_template
        _user_defaults = user_defaults
        _captcha = captcha
        _styles = styles or Styles()
        _read_only = read_only

    return _RegisterEndpoint
