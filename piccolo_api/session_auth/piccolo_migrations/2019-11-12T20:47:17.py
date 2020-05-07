from piccolo.apps.migrations.auto import MigrationManager


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
            "default": None,
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
            "default": None,
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
            "default": None,
            "null": False,
            "primary": False,
            "key": False,
            "unique": False,
            "index": False,
        },
    )

    return manager


async def backwards():
    pass
