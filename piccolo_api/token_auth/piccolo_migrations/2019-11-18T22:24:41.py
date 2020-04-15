from piccolo.migrations.auto import MigrationManager


ID = "2019-11-18T22:24:41"


async def forwards():
    manager = MigrationManager(migration_id=ID)
    manager.add_table("TokenAuth", tablename="token_auth")
    manager.add_column(
        table_class_name="TokenAuth",
        tablename="token_auth",
        column_name="token",
        column_class_name="Varchar",
        params={
            "length": 255,
            "default": None,
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
            "references": "BaseUser|piccolo_user",
            "on_delete": "OnDelete.cascade",
            "on_update": "OnUpdate.cascade",
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
