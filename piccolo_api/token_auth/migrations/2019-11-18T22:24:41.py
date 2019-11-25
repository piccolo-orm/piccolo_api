from piccolo.table import Table
from piccolo.columns import Varchar, ForeignKey


ID = "2019-11-18T22:24:41"


class BaseUser(Table, tablename="piccolo_user"):
    pass


class TokenAuth(Table):
    token = Varchar()
    user = ForeignKey(references=BaseUser)


async def forwards():
    await TokenAuth.create_table().run()


async def backwards():
    await TokenAuth.alter().drop_table().run()
