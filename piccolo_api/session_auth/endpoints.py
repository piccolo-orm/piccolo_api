from abc import abstractproperty, ABCMeta
from datetime import datetime, timedelta
from json import JSONDecodeError
import os
import typing as t
import warnings

from piccolo.extensions.user.tables import BaseUser
from starlette.exceptions import HTTPException
from starlette.endpoints import HTTPEndpoint, Request
from starlette.responses import (
    HTMLResponse,
    RedirectResponse,
    PlainTextResponse,
)
from starlette.status import HTTP_303_SEE_OTHER
from starlette.templating import Jinja2Templates

from piccolo_api.session_auth.tables import SessionsBase


TEMPLATES = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


class SessionLogoutEndpoint(HTTPEndpoint, metaclass=ABCMeta):
    @abstractproperty
    def _session_table(self) -> t.Type[SessionsBase]:
        raise NotImplementedError

    @abstractproperty
    def _cookie_name(self) -> str:
        raise NotImplementedError

    async def post(self, request: Request) -> PlainTextResponse:
        cookie = request.cookies.get(self._cookie_name, None)
        if not cookie:
            raise HTTPException(
                status_code=401, detail="The session cookie wasn't found."
            )
        await self._session_table.remove_session(token=cookie)

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
    def _expiry(self) -> timedelta:
        raise NotImplementedError

    @abstractproperty
    def _cookie_name(self) -> str:
        raise NotImplementedError

    @abstractproperty
    def _redirect_to(self) -> str:
        """
        Where to redirect to after login is successful. It's the name of a
        Starlette route.
        """
        raise NotImplementedError

    @abstractproperty
    def _production(self) -> bool:
        """
        If True, apply more stringent security.
        """
        raise NotImplementedError

    async def get(self, request: Request) -> HTMLResponse:
        template = TEMPLATES.get_template("login.html")
        return HTMLResponse(template.render())

    async def post(self, request: Request) -> RedirectResponse:
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
            raise HTTPException(status_code=401, detail="Login failed")

        expiry_date = datetime.now() + self._expiry

        session: SessionsBase = await self._session_table.create_session(
            user_id=user_id, expiry_date=expiry_date
        )

        response = RedirectResponse(
            url=self._redirect_to, status_code=HTTP_303_SEE_OTHER
        )

        if not self._production:
            message = (
                "If running sessions in production, make sure 'production' "
                "is set to True, and serve under HTTPS."
            )
            warnings.warn(message)

        # TODO - want to set SameSite
        response.set_cookie(
            key=self._cookie_name,
            value=session.token,
            httponly=True,
            secure=self._production,
            max_age=self._expiry.seconds,
        )
        return response


def session_login(
    auth_table: BaseUser = BaseUser,
    session_table: SessionsBase = SessionsBase,
    expiry: timedelta = timedelta(hours=1),
    redirect_to: str = "/",
    production: bool = False,
    cookie_name: str = "id",
) -> t.Type[SessionLoginEndpoint]:
    class _SessionLoginEndpoint(SessionLoginEndpoint):
        _auth_table = auth_table
        _session_table = session_table
        _expiry = expiry
        _redirect_to = redirect_to
        _production = production
        _cookie_name = cookie_name

    return _SessionLoginEndpoint


def session_logout(
    session_table: SessionsBase = SessionsBase, cookie_name: str = "id",
) -> t.Type[SessionLogoutEndpoint]:
    class _SessionLogoutEndpoint(SessionLogoutEndpoint):
        _session_table = session_table
        _cookie_name = cookie_name

    return _SessionLogoutEndpoint
