import dataclasses
import typing as t


@dataclasses.dataclass
class LoginHooks:
    pre_login: t.Optional[t.List[t.Callable]] = None
    login_success: t.Optional[t.List[t.Callable]] = None
    login_failure: t.Optional[t.List[t.Callable]] = None
