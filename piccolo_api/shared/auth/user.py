from __future__ import annotations
import typing as t

from piccolo.apps.user.tables import BaseUser as PiccoloBaseUser
from starlette.authentication import BaseUser


class User(BaseUser):
    def __init__(
        self, auth_table: t.Type[PiccoloBaseUser], user_id: int, username: str
    ):
        super().__init__()
        self.auth_table = auth_table
        self.user_id = user_id
        self.username = username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username

    @property
    def identity(self) -> str:
        return str(self.user_id)
