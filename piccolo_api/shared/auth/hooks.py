from __future__ import annotations

import dataclasses
import typing as t

from piccolo.apps.user.tables import BaseUser

PreLoginHook = t.Callable[[str, str], t.Optional[str]]
LoginSuccessHook = t.Callable[[BaseUser], t.Optional[str]]
LoginFailureHook = t.Callable[[str, str], t.Optional[str]]


@dataclasses.dataclass
class LoginHooks:
    """
    Allows you to run custom logic during login. A hook can be a function or
    coroutine.

    Here's an example using :class:`session_login <piccolo_api.session_auth.endpoints.session_login>`:

    .. code-block:: python

        def check_ban_list(username: str, password: str):
            '''
            An example pre_login hook.
            '''
            if username in ('nuisance@pest.com',):
                return 'This account has been temporarily suspended'.


        def send_email(user: BaseUser):
            '''
            An example login_success hook.
            '''
            await my_email_service.send(
                user.email,
                'Your account was just logged in to.'
            )


        async def log_failed(username: str, password: str):
            '''
            An example login_failure hook.
            '''
            await my_logging_service.record(f'{username} could not login')
            return (
                'To reset your password go <a href="/password-reset/">here</a>.'
            )


        login_endpoint = session_login(
            hooks=LoginHooks(
                pre_login=[check_ban_list],
                login_success=[send_email],
                login_failure=[log_failed],
            )
        )

    If any of the hooks return a string, the login process is aborted, and the
    login template is shown again, containing the string as a warning message.
    The string can contain HTML such as links, and it will be rendered
    correctly.

    If any of the hooks raise an ``Exception``, then a generic error message is
    shown in the login template.

    :param pre_login:
        A list of function and / or coroutines, which accept the username and
        password as a string.
    :param login_success:
        A list of function and / or coroutines, which accept a :class:`BaseUser <piccolo.apps.user.tables.BaseUser>`.
        instance. If a string is returned, or an ``Exception`` is raised, the
        login process stops before a session is created.
    :param login_failure:
        A list of function and / or coroutines, which accept the username and
        password as a string.

    """  # noqa: E501

    pre_login: t.Optional[t.List[PreLoginHook]] = None
    login_success: t.Optional[t.List[LoginSuccessHook]] = None
    login_failure: t.Optional[t.List[LoginFailureHook]] = None
