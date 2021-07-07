from __future__ import annotations
import typing as t

from piccolo.apps.user.tables import BaseUser as PiccoloBaseUser
from starlette.authentication import BaseUser

if t.TYPE_CHECKING:
    from piccolo.table import Table


class User(BaseUser):
    def __init__(self, user: PiccoloBaseUser):
        super().__init__()
        self.user = user

    ###########################################################################
    # For backwards compatibility - these used to be arguments to the
    # contructor, but we can just infer them from the user instance.

    @property
    def auth_table(self) -> t.Type[Table]:
        return self.user.__class__

    @property
    def user_id(self) -> int:
        return t.cast(int, self.user.id)

    @property
    def username(self) -> str:
        return t.cast(str, self.user.username)

    ###########################################################################
    # Required properties.

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username

    @property
    def identity(self) -> str:
        return str(self.user_id)


class UnauthenticatedUser(BaseUser):
    def __init__(self):
        super().__init__()
        self.user = None

    @property
    def is_authenticated(self) -> bool:
        return False

    @property
    def display_name(self) -> str:
        return ""

    @property
    def identity(self) -> str:
        return ""
