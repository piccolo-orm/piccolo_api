from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Integer, Text, Timestamptz, Varchar
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod

ID = "2024-08-08T21:41:46:837552"
VERSION = "1.16.0"
DESCRIPTION = "Add AuthenticatorSecret table"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="mfa_authenticator", description=DESCRIPTION
    )

    manager.add_table(
        class_name="AuthenticatorSecret",
        tablename="authenticator_secret",
        schema=None,
        columns=None,
    )

    manager.add_column(
        table_class_name="AuthenticatorSecret",
        tablename="authenticator_secret",
        column_name="user_id",
        db_column_name="user_id",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="AuthenticatorSecret",
        tablename="authenticator_secret",
        column_name="device_name",
        db_column_name="device_name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="AuthenticatorSecret",
        tablename="authenticator_secret",
        column_name="secret",
        db_column_name="secret",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": True,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="AuthenticatorSecret",
        tablename="authenticator_secret",
        column_name="created_at",
        db_column_name="created_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="AuthenticatorSecret",
        tablename="authenticator_secret",
        column_name="revoked_at",
        db_column_name="revoked_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="AuthenticatorSecret",
        tablename="authenticator_secret",
        column_name="last_used_at",
        db_column_name="last_used_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="AuthenticatorSecret",
        tablename="authenticator_secret",
        column_name="last_used_code",
        db_column_name="last_used_code",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
