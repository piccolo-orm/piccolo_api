from __future__ import annotations

import dataclasses
import inspect
import logging
import typing as t

PreLoginHook = t.Union[
    t.Callable[[str], t.Optional[str]],
    t.Callable[[str], t.Awaitable[t.Optional[str]]],
]
LoginSuccessHook = t.Union[
    t.Callable[[str, int], t.Optional[str]],
    t.Callable[[str, int], t.Awaitable[t.Optional[str]]],
]
LoginFailureHook = t.Union[
    t.Callable[[str], t.Optional[str]],
    t.Callable[[str], t.Awaitable[t.Optional[str]]],
]


logger = logging.getLogger(__file__)


@dataclasses.dataclass
class LoginHooks:
    """
    Allows you to run custom logic during login. A hook can be a function or
    coroutine.

    Here's an example using :class:`session_login <piccolo_api.session_auth.endpoints.session_login>`:

    .. code-block:: python

        def check_ban_list(username: str, **kwargs):
            '''
            An example `pre_login` hook.
            '''
            if username in ('nuisance', 'pest'):
                return 'This account has been temporarily suspended'.


        async def log_success(username: str, user_id: int, **kwargs):
            '''
            An example `login_success` hook.
            '''
            await my_logging_service.record(
                f'{username} just logged in'
            )


        async def log_failure(username: str, **kwargs):
            '''
            An example `login_failure` hook.
            '''
            await my_logging_service.record(f'{username} could not login')
            return (
                'To reset your password go <a href="/password-reset/">here</a>.'
            )


        login_endpoint = session_login(
            hooks=LoginHooks(
                pre_login=[check_ban_list],
                login_success=[log_success],
                login_failure=[log_failure],
            )
        )

    If any of the hooks return a string, the login process is aborted, and the
    login template is shown again, containing the string as a warning message.
    The string can contain HTML such as links, and it will be rendered
    correctly.

    All of the example hooks above accept ``**kwargs`` - this is recommended
    just in case more data is passed to the hooks in future Piccolo API
    versions.

    :param pre_login:
        A list of function and / or coroutines, which accept the username as a
        string.
    :param login_success:
        A list of function and / or coroutines, which accept the username as a
        string, and the user ID as an integer. If a string is returned, the
        login process stops before a session is created.
    :param login_failure:
        A list of function and / or coroutines, which accept the username as a
        string.

    """  # noqa: E501

    pre_login: t.Optional[t.List[PreLoginHook]] = None
    login_success: t.Optional[t.List[LoginSuccessHook]] = None
    login_failure: t.Optional[t.List[LoginFailureHook]] = None

    async def run_pre_login(self, username: str) -> t.Optional[str]:
        if self.pre_login:
            for hook in self.pre_login:
                response = hook(username)
                if inspect.isawaitable(response):
                    response = t.cast(t.Awaitable, response)
                    response = await response

                if isinstance(response, str):
                    return response

        return None

    async def run_login_success(
        self, username: str, user_id: int
    ) -> t.Optional[str]:
        if self.login_success:
            for hook in self.login_success:
                response = hook(username, user_id)
                if inspect.isawaitable(response):
                    response = t.cast(t.Awaitable, response)
                    response = await response

                if isinstance(response, str):
                    return response

        return None

    async def run_login_failure(self, username: str) -> t.Optional[str]:
        if self.login_failure:
            for hook in self.login_failure:
                response = hook(username)
                if inspect.isawaitable(response):
                    response = t.cast(t.Awaitable, response)
                    response = await response

                if isinstance(response, str):
                    return response

        return None
