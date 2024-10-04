from __future__ import annotations

import os
import typing as t
import warnings
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from json import JSONDecodeError

from jinja2 import Environment, FileSystemLoader
from piccolo.apps.user.tables import BaseUser
from starlette.endpoints import HTTPEndpoint, Request
from starlette.exceptions import HTTPException
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED

from piccolo_api.mfa.provider import MFAProvider
from piccolo_api.session_auth.tables import SessionsBase
from piccolo_api.shared.auth.hooks import LoginHooks
from piccolo_api.shared.auth.styles import Styles

if t.TYPE_CHECKING:  # pragma: no cover
    from jinja2 import Template
    from starlette.responses import Response

    from piccolo_api.shared.auth.captcha import Captcha

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "templates"
)

LOGIN_TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "session_login.html")

LOGOUT_TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "session_logout.html")


class SessionLogoutEndpoint(HTTPEndpoint, metaclass=ABCMeta):
    @property
    @abstractmethod
    def _session_table(self) -> t.Type[SessionsBase]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _cookie_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def _redirect_to(self) -> t.Optional[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _logout_template(self) -> Template:
        raise NotImplementedError

    @property
    @abstractmethod
    def _styles(self) -> t.Optional[Styles]:
        raise NotImplementedError

    def _render_template(
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
                styles=self._styles,
                **template_context,
            )
        )

    async def get(self, request: Request) -> HTMLResponse:
        return self._render_template(request)

    async def post(self, request: Request) -> Response:
        cookie = request.cookies.get(self._cookie_name, None)
        if not cookie:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="The session cookie wasn't found.",
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
    @property
    @abstractmethod
    def _auth_table(self) -> t.Type[BaseUser]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _session_table(self) -> t.Type[SessionsBase]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _session_expiry(self) -> timedelta:
        raise NotImplementedError

    @property
    @abstractmethod
    def _max_session_expiry(self) -> timedelta:
        raise NotImplementedError

    @property
    @abstractmethod
    def _cookie_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def _redirect_to(self) -> t.Optional[str]:
        """
        Where to redirect to after login is successful.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def _production(self) -> bool:
        """
        If True, apply more stringent security.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def _login_template(self) -> Template:
        raise NotImplementedError

    @property
    @abstractmethod
    def _hooks(self) -> t.Optional[LoginHooks]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _captcha(self) -> t.Optional[Captcha]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _styles(self) -> t.Optional[Styles]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _mfa_providers(self) -> t.Optional[t.Sequence[MFAProvider]]:
        raise NotImplementedError

    def _render_template(
        self,
        request: Request,
        template_context: t.Dict[str, t.Any] = {},
        status_code=200,
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
                captcha=self._captcha,
                styles=self._styles,
                **template_context,
            ),
            status_code=status_code,
        )

    def _get_error_response(
        self, request, error: str, response_format: t.Literal["html", "plain"]
    ) -> Response:
        if response_format == "html":
            return self._render_template(
                request,
                template_context={"error": error},
                status_code=HTTP_401_UNAUTHORIZED,
            )
        else:
            return PlainTextResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content=f"Login failed: {error}",
            )

    async def get(self, request: Request) -> HTMLResponse:
        return self._render_template(request)

    async def post(self, request: Request) -> Response:
        # Some middleware (for example CSRF) has already awaited the request
        # body, and adds it to the request.
        body: t.Any = request.scope.get("form")

        if not body:
            try:
                body = await request.json()
            except JSONDecodeError:
                body = await request.form()

        username = body.get("username")
        password = body.get("password")
        return_html = body.get("format") == "html"

        if (not username) or (not password):
            error_message = "Missing username or password"
            if return_html:
                return self._render_template(
                    request,
                    template_context={"error": error_message},
                )
            else:
                raise HTTPException(status_code=422, detail=error_message)

        # Run pre_login hooks
        if self._hooks and self._hooks.pre_login:
            hooks_response = await self._hooks.run_pre_login(username=username)
            if isinstance(hooks_response, str):
                return self._get_error_response(
                    request=request,
                    error=hooks_response,
                    response_format="html" if return_html else "plain",
                )

        # Check CAPTCHA
        if self._captcha:
            token = body.get(self._captcha.token_field, None)
            validate_response = await self._captcha.validate(token=token)
            if isinstance(validate_response, str):
                if return_html:
                    return self._render_template(
                        request,
                        template_context={"error": validate_response},
                    )
                else:
                    raise HTTPException(
                        status_code=HTTP_401_UNAUTHORIZED,
                        detail=validate_response,
                    )

        # Attempt login
        user_id = await self._auth_table.login(
            username=username, password=password
        )

        if user_id:
            # Apply MFA
            if mfa_providers := self._mfa_providers:
                user = (
                    await self._auth_table.objects()
                    .where(self._auth_table.id == user_id)
                    .first()
                )

                assert user is not None

                if enrolled_mfa_providers := [
                    mfa_provider
                    for mfa_provider in mfa_providers
                    if await mfa_provider.is_user_enrolled(user=user)
                ]:
                    mfa_code = body.get("mfa_code")

                    if mfa_code is None:
                        has_sent_code: t.List[bool] = []
                        for mfa_provider in enrolled_mfa_providers:
                            # Send the code (only used with things like email
                            # and SMS MFA).
                            has_sent_code.append(
                                await mfa_provider.send_code(user=user)
                            )

                        message = "MFA code required"
                        if any(has_sent_code):
                            message += " (we sent you a code)"

                        if return_html:
                            return self._render_template(
                                request,
                                template_context={
                                    "error": message,
                                    "show_mfa_input": True,
                                    "mfa_provider_names": [
                                        mfa_provider.name
                                        for mfa_provider in enrolled_mfa_providers  # noqa: E501
                                    ],
                                },
                            )
                        else:
                            raise HTTPException(
                                status_code=HTTP_401_UNAUTHORIZED,
                                detail=message,
                            )

                    # Work out which MFA provider to use:
                    if len(enrolled_mfa_providers) == 1:
                        active_mfa_provider = enrolled_mfa_providers[0]
                    else:
                        mfa_provider_name = body.get("mfa_provider_name")

                        if mfa_provider_name is None:
                            raise HTTPException(
                                status_code=HTTP_401_UNAUTHORIZED,
                                detail="MFA provider must be specified",
                            )

                        filtered_mfa_providers = [
                            i
                            for i in enrolled_mfa_providers
                            if i.name == mfa_provider_name
                        ]

                        if len(filtered_mfa_providers) == 0:
                            raise HTTPException(
                                status_code=HTTP_401_UNAUTHORIZED,
                                detail="MFA provider not recognised.",
                            )

                        if len(filtered_mfa_providers) > 1:
                            raise HTTPException(
                                status_code=HTTP_401_UNAUTHORIZED,
                                detail=(
                                    "Multiple matching MFA providers found."
                                ),
                            )

                        active_mfa_provider = filtered_mfa_providers[0]

                    if not await active_mfa_provider.authenticate_user(
                        user=user, code=mfa_code
                    ):
                        if return_html:
                            return self._render_template(
                                request,
                                template_context={
                                    "error": "MFA failed",
                                    "show_mfa_input": True,
                                    "mfa_provider_names": {
                                        mfa_provider.name
                                        for mfa_provider in enrolled_mfa_providers  # noqa: E501
                                    },
                                },
                            )
                        else:
                            raise HTTPException(
                                status_code=HTTP_401_UNAUTHORIZED,
                                detail="MFA failed",
                            )

            # Run login_success hooks
            if self._hooks and self._hooks.login_success:
                hooks_response = await self._hooks.run_login_success(
                    username=username, user_id=user_id
                )
                if isinstance(hooks_response, str):
                    return self._get_error_response(
                        request=request,
                        error=hooks_response,
                        response_format="html" if return_html else "plain",
                    )
        else:
            # Run login_failure hooks
            if self._hooks and self._hooks.login_failure:
                hooks_response = await self._hooks.run_login_failure(
                    username=username
                )
                if isinstance(hooks_response, str):
                    return self._get_error_response(
                        request=request,
                        error=hooks_response,
                        response_format="html" if return_html else "plain",
                    )

            if return_html:
                return self._render_template(
                    request,
                    template_context={
                        "error": "The username or password is incorrect."
                    },
                )
            else:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, detail="Login failed"
                )

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
    hooks: t.Optional[LoginHooks] = None,
    captcha: t.Optional[Captcha] = None,
    styles: t.Optional[Styles] = None,
    mfa_providers: t.Optional[t.Sequence[MFAProvider]] = None,
) -> t.Type[SessionLoginEndpoint]:
    """
    An endpoint for creating a user session.

    :param auth_table:
        Which table to authenticate the username and password with. It
        defaults to :class:`BaseUser <piccolo.apps.user.tables.BaseUser>`.
    :param session_table:
        Which table to store the session in. If defaults to
        :class:`SessionsBase <piccolo_api.session_auth.tables.SessionsBase>`.
    :param session_expiry:
        How long the session will last.
    :param max_session_expiry:
        If the session is refreshed (see the ``increase_expiry`` parameter for
        :class:`SessionsAuthBackend <piccolo_api.session_auth.middleware.SessionsAuthBackend>`),
        it can only be refreshed up to a certain limit, after which the session
        is void.
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
        ``piccolo_api/templates/session_login.html`` as a basis for your
        custom template.
    :param hooks:
        Allows you to run custom logic at various points in the login process.
        See :class:`LoginHooks <piccolo_api.shared.auth.hooks.LoginHooks>`.
    :param captcha:
        Integrate a CAPTCHA service, to provide protection against bots.
        See :class:`Captcha <piccolo_api.shared.auth.captcha.Captcha>`.
    :param styles:
        Modify the appearance of the HTML template using CSS.
    :param mfa_providers:
        Add additional security to the login process using Multi-Factor
        Authentication.

    """  # noqa: E501
    template_path = (
        LOGIN_TEMPLATE_PATH if template_path is None else template_path
    )

    directory, filename = os.path.split(template_path)
    environment = Environment(
        loader=FileSystemLoader(directory), autoescape=True
    )
    login_template = environment.get_template(filename)

    class _SessionLoginEndpoint(SessionLoginEndpoint):
        _auth_table = auth_table
        _session_table = session_table
        _session_expiry = session_expiry
        _max_session_expiry = max_session_expiry
        _redirect_to = redirect_to
        _production = production
        _cookie_name = cookie_name
        _login_template = login_template
        _hooks = hooks
        _captcha = captcha
        _styles = styles or Styles()
        _mfa_providers = mfa_providers

    return _SessionLoginEndpoint


def session_logout(
    session_table: t.Type[SessionsBase] = SessionsBase,
    cookie_name: str = "id",
    redirect_to: t.Optional[str] = None,
    template_path: t.Optional[str] = None,
    styles: t.Optional[Styles] = None,
) -> t.Type[SessionLogoutEndpoint]:
    """
    An endpoint for clearing a user session.

    :param session_table:
        Which table to store the session in. It defaults to
        :class:`SessionsBase <piccolo_api.session_auth.tables.SessionsBase>`.
    :param cookie_name:
        The name of the cookie used to store the session token. Only override
        this if the name of the cookie clashes with other cookies.
    :param redirect_to:
        Where to redirect to after logging out.
    :param template_path:
        If you want to override the default logout HTML template, you can do
        so by specifying the absolute path to a custom template. For example
        ``'/some_directory/logout.html'``. Refer to the default template at
        ``piccolo_api/templates/logout.html`` as a basis for your
        custom template.
    :param styles:
        Modify the appearance of the HTML template using CSS.

    """  # noqa: E501
    template_path = (
        LOGOUT_TEMPLATE_PATH if template_path is None else template_path
    )

    directory, filename = os.path.split(template_path)
    environment = Environment(
        loader=FileSystemLoader(directory), autoescape=True
    )
    logout_template = environment.get_template(filename)

    class _SessionLogoutEndpoint(SessionLogoutEndpoint):
        _session_table = session_table
        _cookie_name = cookie_name
        _redirect_to = redirect_to
        _logout_template = logout_template
        _styles = styles or Styles()

    return _SessionLogoutEndpoint
