from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Varchar

ID = "2026-05-27T16:15:06:677127"
VERSION = "1.34.0"
DESCRIPTION = "Make token column secret."


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="session_auth", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="SessionsBase",
        tablename="sessions",
        column_name="token",
        db_column_name="token",
        params={"secret": True},
        old_params={"secret": False},
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    return manager
