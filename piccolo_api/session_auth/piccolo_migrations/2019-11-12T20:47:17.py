from piccolo.apps.migrations.auto import MigrationManager
from piccolo.columns.defaults.timestamp import TimestampOffset


ID = "2019-11-12T20:47:17"


async def forwards():
    manager = MigrationManager(migration_id=ID)
    manager.add_table("SessionsBase", tablename="sessions")
    manager.add_column(
        table_class_name="SessionsBase",
        tablename="sessions",
        column_name="token",
        column_class_name="Varchar",
        params={
            "length": 100,
            "default": "",
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )
    manager.add_column(
        table_class_name="SessionsBase",
        tablename="sessions",
        column_name="user_id",
        column_class_name="Integer",
        params={
            "default": 0,
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )
    manager.add_column(
        table_class_name="SessionsBase",
        tablename="sessions",
        column_name="expiry_date",
        column_class_name="Timestamp",
        params={
            "default": TimestampOffset(hours=1),
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )
    manager.add_column(
        table_class_name="SessionsBase",
        tablename="sessions",
        column_name="max_expiry_date",
        column_class_name="Timestamp",
        params={
            "default": TimestampOffset(days=7),
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )

    return manager
