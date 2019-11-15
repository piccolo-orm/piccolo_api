import secrets

from piccolo.columns.column_types import Varchar, ForeignKey
from piccolo.extensions.user.tables import BaseUser
from piccolo.table import Table


class TokenAuth(Table):
    """
    Holds randomly generated tokens.

    Useful for mobile authentication, IOT etc. Session auth is recommended for
    web usage.
    """
    token = Varchar()
    user = ForeignKey(references=BaseUser)

    @classmethod
    def create_token(user_id: int):
        pass
