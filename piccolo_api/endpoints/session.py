from abc import abstractproperty
from datetime import datetime, timedelta
from json import JSONDecodeError
import os
import typing as t
import warnings

from piccolo.extensions.user import BaseUser
from starlette.exceptions import HTTPException
from starlette.endpoints import HTTPEndpoint, Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from starlette.templating import Jinja2Templates

from piccolo_api.tables.sessions import SessionsBase


TEMPLATES = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


class SessionLoginEndpoint(HTTPEndpoint):
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
    def _redirect_to(self) -> str:
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
                "is set to True"
            )
            warnings.warn(message)

        # TODO - want to set SameSite
        response.set_cookie(
            key="id",
            value=session.token,
            httponly=True,
            secure=self._production,
        )
        return response


def session_login(
    auth_table: BaseUser,
    session_table: SessionsBase,
    expiry: timedelta = timedelta(hours=1),
    redirect_to: str = "/",
    production: bool = False,
) -> t.Type[SessionLoginEndpoint]:
    class _SessionLoginEndpoint(SessionLoginEndpoint):
        _auth_table = auth_table
        _session_table = session_table
        _expiry = expiry
        _redirect_to = redirect_to
        _production = production

    return _SessionLoginEndpoint
