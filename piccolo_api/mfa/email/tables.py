from piccolo.columns import Email, Timestamptz, Varchar
from piccolo.table import Table


class EmailCode(Table):
    email = Email()
    code = Varchar()
    created_at = Timestamptz()
    used_at = Timestamptz(null=True, default=None)
