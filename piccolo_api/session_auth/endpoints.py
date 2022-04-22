from __future__ import annotations

import os
import re
import typing as t
import warnings
from abc import ABCMeta, abstractproperty
from datetime import datetime, timedelta
from json import JSONDecodeError

from jinja2 import Environment, FileSystemLoader
from piccolo.apps.user.tables import BaseUser
from starlette.datastructures import URL
from starlette.endpoints import HTTPEndpoint, Request
from starlette.exceptions import HTTPException
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from starlette.status import HTTP_303_SEE_OTHER

from piccolo_api.session_auth.tables import SessionsBase

if t.TYPE_CHECKING:  # pragma: no cover
    from jinja2 import Template
    from starlette.responses import Response


LOGIN_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "templates", "login.html"
)

SIGNUP_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "templates", "signup.html"
)

LOGOUT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "templates", "logout.html"
)


class SessionLogoutEndpoint(HTTPEndpoint, metaclass=ABCMeta):
    @abstractproperty
    def _session_table(self) -> t.Type[SessionsBase]:
        raise NotImplementedError

    @abstractproperty
    def _cookie_name(self) -> str:
        raise NotImplementedError

    @abstractproperty
    def _redirect_to(self) -> t.Optional[str]:
        raise NotImplementedError

    @abstractproperty
    def _logout_template(self) -> Template:
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
            self._logout_template.render(
                csrftoken=csrftoken,
                csrf_cookie_name=csrf_cookie_name,
                request=request,
                **template_context,
            )
        )

    async def get(self, request: Request) -> HTMLResponse:
        return self.render_template(request)

    async def post(self, request: Request) -> Response:
        cookie = request.cookies.get(self._cookie_name, None)
        if not cookie:
            raise HTTPException(
                status_code=401, detail="The session cookie wasn't found."
            )
        await self._session_table.remove_session(token=cookie)

        if self._redirect_to is not None:
            response: Response = RedirectResponse(
                url=self._redirect_to, status_code=HTTP_303_SEE_OTHER
            )
        else:
            response = PlainTextResponse("Successfully logged out")

        response.set_cookie(self._cookie_name, "", max_age=0)
        return response


class SessionLoginEndpoint(HTTPEndpoint, metaclass=ABCMeta):
    @abstractproperty
    def _auth_table(self) -> t.Type[BaseUser]:
        raise NotImplementedError

    @abstractproperty
    def _session_table(self) -> t.Type[SessionsBase]:
        raise NotImplementedError

    @abstractproperty
    def _session_expiry(self) -> timedelta:
        raise NotImplementedError

    @abstractproperty
    def _max_session_expiry(self) -> timedelta:
        raise NotImplementedError

    @abstractproperty
    def _cookie_name(self) -> str:
        raise NotImplementedError

    @abstractproperty
    def _redirect_to(self) -> t.Optional[str]:
        """
        Where to redirect to after login is successful.
        """
        raise NotImplementedError

    @abstractproperty
    def _production(self) -> bool:
        """
        If True, apply more stringent security.
        """
        raise NotImplementedError

    @abstractproperty
    def _login_template(self) -> Template:
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
            self._login_template.render(
                csrftoken=csrftoken,
                csrf_cookie_name=csrf_cookie_name,
                request=request,
                **template_context,
            )
        )

    async def get(self, request: Request) -> HTMLResponse:
        return self.render_template(request)

    async def post(self, request: Request) -> Response:
        # Some middleware (for example CSRF) has already awaited the request
        # body, and adds it to the request.
        body = request.scope.get("form")

        if not body:
            try:
                body = await request.json()
            except JSONDecodeError:
                body = await request.form()

        username = body.get("username", None)
        password = body.get("password", None)

        if (not username) or (not password):
            raise HTTPException(
                status_code=401, detail="Missing username or password"
            )

        user_id = await self._auth_table.login(
            username=username, password=password
        )

        if not user_id:
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={
                        "error": "The username or password is incorrect."
                    },
                )
            else:
                raise HTTPException(status_code=401, detail="Login failed")

        now = datetime.now()
        expiry_date = now + self._session_expiry
        max_expiry_date = now + self._max_session_expiry

        session: SessionsBase = await self._session_table.create_session(
            user_id=user_id,
            expiry_date=expiry_date,
            max_expiry_date=max_expiry_date,
        )

        if self._redirect_to is not None:
            response: Response = RedirectResponse(
                url=self._redirect_to, status_code=HTTP_303_SEE_OTHER
            )
        else:
            response = JSONResponse(
                content={"message": "logged in"}, status_code=200
            )

        if not self._production:
            message = (
                "If running sessions in production, make sure 'production' "
                "is set to True, and serve under HTTPS."
            )
            warnings.warn(message)

        cookie_value = t.cast(str, session.token)

        response.set_cookie(
            key=self._cookie_name,
            value=cookie_value,
            httponly=True,
            secure=self._production,
            max_age=int(self._max_session_expiry.total_seconds()),
            samesite="lax",
        )
        return response


class SignupEndpoint(HTTPEndpoint, metaclass=ABCMeta):
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
    def _signup_template(self) -> Template:
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
            self._signup_template.render(
                csrftoken=csrftoken,
                csrf_cookie_name=csrf_cookie_name,
                request=request,
                **template_context,
            )
        )

    async def get(self, request: Request) -> HTMLResponse:
        return self.render_template(request)

    async def post(self, request: Request) -> Response:
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

        if (
            (not username)
            or (not email)
            or (not password)
            or (not confirm_password)
        ):
            raise HTTPException(
                status_code=401,
                detail="Form is invalid. Missing one or more fields.",
            )

        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

        if not re.fullmatch(email_regex, email):
            if body.get("format") == "html":
                return self.render_template(
                    request,
                    template_context={"error": "Not valid email address."},
                )
            else:
                raise HTTPException(
                    status_code=401, detail="Not valid email address."
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
                    status_code=401,
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
                    status_code=401, detail="Passwords do not match."
                )

        if (
            await self._auth_table.exists()
            .where(self._auth_table.email == email)
            .run()
            or await self._auth_table.exists()
            .where(self._auth_table.username == username)
            .run()
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
                    status_code=401,
                    detail="User with email or username already exists.",
                )

        query = self._auth_table(
            username=username,
            email=email,
            password=password,
        )
        # save user to database
        await query.save().run()

        return RedirectResponse(
            url=self._redirect_to, status_code=HTTP_303_SEE_OTHER
        )


def session_login(
    auth_table: t.Optional[t.Type[BaseUser]] = None,
    session_table: t.Optional[t.Type[SessionsBase]] = None,
    session_expiry: timedelta = timedelta(hours=1),
    max_session_expiry: timedelta = timedelta(days=7),
    redirect_to: t.Optional[str] = "/",
    production: bool = False,
    cookie_name: str = "id",
    template_path: t.Optional[str] = None,
) -> t.Type[SessionLoginEndpoint]:
    """
    An endpoint for creating a user session.

    :param auth_table:
        Which table to authenticate the username and password with. If not
        specified, it defaults to ``BaseUser``.
    :param session_table:
        Which table to store the session in. If not specified, it defaults to
        ``SessionsBase``.
    :param session_expiry:
        How long the session will last.
    :param max_session_expiry:
        If the session is refreshed (see the ``increase_expiry`` parameter for
        ``SessionsAuthBackend``), it can only be refreshed up to a certain
        limit, after which the session is void.
    :param redirect_to:
        Where to redirect to after successful login.
    :param production:
        Adds additional security measures. Use this in production, when serving
        your app over HTTPS.
    :param cookie_name:
        The name of the cookie used to store the session token. Only override
        this if the name of the cookie clashes with other cookies.
    :param template_path:
        If you want to override the default login HTML template, you can do
        so by specifying the absolute path to a custom template. For example
        ``'/some_directory/login.html'``. Refer to the default template at
        ``piccolo_api/session_auth/templates/login.html`` as a basis for your
        custom template.

    """
    template_path = (
        LOGIN_TEMPLATE_PATH if template_path is None else template_path
    )

    directory, filename = os.path.split(template_path)
    environment = Environment(loader=FileSystemLoader(directory))
    login_template = environment.get_template(filename)

    class _SessionLoginEndpoint(SessionLoginEndpoint):
        _auth_table = auth_table or BaseUser
        _session_table = session_table or SessionsBase
        _session_expiry = session_expiry
        _max_session_expiry = max_session_expiry
        _redirect_to = redirect_to
        _production = production
        _cookie_name = cookie_name
        _login_template = login_template

    return _SessionLoginEndpoint


def signup(
    auth_table: t.Optional[t.Type[BaseUser]] = None,
    redirect_to: t.Union[str, URL] = "/login/",
    template_path: t.Optional[str] = None,
) -> t.Type[SignupEndpoint]:
    """
    An endpoint for register user.

    :param auth_table:
        Which table to authenticate the username and password with. If not
        specified, it defaults to ``BaseUser``.
    :param redirect_to:
        Where to redirect to after successful signup.
    :param template_path:
        If you want to override the default signup HTML template, you can do
        so by specifying the absolute path to a custom template. For example
        ``'/some_directory/signup.html'``. Refer to the default template at
        ``piccolo_api/session_auth/templates/signup.html`` as a basis for your
        custom template.

    """
    template_path = (
        SIGNUP_TEMPLATE_PATH if template_path is None else template_path
    )

    directory, filename = os.path.split(template_path)
    environment = Environment(loader=FileSystemLoader(directory))
    signup_template = environment.get_template(filename)

    class _SignupEndpoint(SignupEndpoint):
        _auth_table = auth_table or BaseUser
        _redirect_to = redirect_to
        _signup_template = signup_template

    return _SignupEndpoint


def session_logout(
    session_table: t.Optional[t.Type[SessionsBase]] = None,
    cookie_name: str = "id",
    redirect_to: t.Optional[str] = None,
    template_path: t.Optional[str] = None,
) -> t.Type[SessionLogoutEndpoint]:
    """
    An endpoint for clearing a user session.

    :param session_table:
        Which table to store the session in. If not specified, it defaults
        to :class:`SessionsBase`.
    :param cookie_name:
        The name of the cookie used to store the session token. Only override
        this if the name of the cookie clashes with other cookies.
    :param redirect_to:
        Where to redirect to after logging out.
    :param template_path:
        If you want to override the default logout HTML template, you can do
        so by specifying the absolute path to a custom template. For example
        ``'/some_directory/logout.html'``. Refer to the default template at
        ``piccolo_api/session_auth/templates/logout.html`` as a basis for your
        custom template.
    """
    template_path = (
        LOGOUT_TEMPLATE_PATH if template_path is None else template_path
    )

    directory, filename = os.path.split(template_path)
    environment = Environment(loader=FileSystemLoader(directory))
    logout_template = environment.get_template(filename)

    class _SessionLogoutEndpoint(SessionLogoutEndpoint):
        _session_table = session_table or SessionsBase
        _cookie_name = cookie_name
        _redirect_to = redirect_to
        _logout_template = logout_template

    return _SessionLogoutEndpoint
