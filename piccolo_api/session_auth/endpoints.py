from __future__ import annotations
from abc import abstractproperty, ABCMeta
from datetime import datetime, timedelta
from jinja2 import Template
from json import JSONDecodeError
import os
import typing as t
import warnings

from piccolo.apps.user.tables import BaseUser
from starlette.exceptions import HTTPException
from starlette.endpoints import HTTPEndpoint, Request
from starlette.responses import (
    HTMLResponse,
    RedirectResponse,
    PlainTextResponse,
    JSONResponse,
)
from starlette.status import HTTP_303_SEE_OTHER

from piccolo_api.session_auth.tables import SessionsBase


if t.TYPE_CHECKING:
    from starlette.responses import Response


LOGIN_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "templates", "login.html"
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
                **template_context
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


def session_login(
    auth_table: t.Type[BaseUser] = BaseUser,
    session_table: t.Type[SessionsBase] = SessionsBase,
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
        Which table to authenticate the username and password with.
    :param session_table:
        Which table to store the session in.
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
    with open(template_path, "r") as f:
        login_template = Template(f.read())

    class _SessionLoginEndpoint(SessionLoginEndpoint):
        _auth_table = auth_table
        _session_table = session_table
        _session_expiry = session_expiry
        _max_session_expiry = max_session_expiry
        _redirect_to = redirect_to
        _production = production
        _cookie_name = cookie_name
        _login_template = login_template

    return _SessionLoginEndpoint


def session_logout(
    session_table: t.Type[SessionsBase] = SessionsBase,
    cookie_name: str = "id",
    redirect_to: t.Optional[str] = None,
) -> t.Type[SessionLogoutEndpoint]:
    """
    An endpoint for clearing a user session.

    :param session_table:
        Which table to store the session in.
    :param cookie_name:
        The name of the cookie used to store the session token. Only override
        this if the name of the cookie clashes with other cookies.
    :param redirect_to:
        Where to redirect to after logging out.
    """

    class _SessionLogoutEndpoint(SessionLogoutEndpoint):
        _session_table = session_table
        _cookie_name = cookie_name
        _redirect_to = redirect_to

    return _SessionLogoutEndpoint
