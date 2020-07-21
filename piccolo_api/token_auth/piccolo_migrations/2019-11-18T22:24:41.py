from piccolo.apps.migrations.auto import MigrationManager
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.table import Table
from piccolo_api.token_auth.tables import generate_token


class BaseUser(Table, tablename="piccolo_user"):
    pass


ID = "2019-11-18T22:24:41"
VERSION = "0.11.8"


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="token_auth")

    manager.add_table("TokenAuth", tablename="token_auth")

    manager.add_column(
        table_class_name="TokenAuth",
        tablename="token_auth",
        column_name="token",
        column_class_name="Varchar",
        params={
            "length": 255,
            "default": generate_token,
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )

    manager.add_column(
        table_class_name="TokenAuth",
        tablename="token_auth",
        column_name="user",
        column_class_name="ForeignKey",
        params={
            "references": BaseUser,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "default": None,
            "null": True,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )

    return manager
