from piccolo.table import Table
from piccolo.columns import Varchar, Integer, Timestamp


ID = "2019-11-12T20:47:17"


class SessionsBase(Table, tablename="sessions"):
    token = Varchar(length=100, null=False)
    user_id = Integer(null=False)
    expiry_date = Timestamp(null=False)
    max_expiry_date = Timestamp(null=False)


async def forwards():
    await SessionsBase.create_table().run()


async def backwards():
    await SessionsBase.alter().drop_table().run()
