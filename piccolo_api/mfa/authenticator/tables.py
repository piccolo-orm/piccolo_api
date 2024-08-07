from piccolo.columns import Integer, Serial, Text, Timestamptz
from piccolo.table import Table


class AuthenticatorSeed(Table):
    id: Serial
    user_id = Integer(null=False)
    code = Text()
    created_at = Timestamptz()
