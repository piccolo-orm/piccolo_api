import os

from piccolo.conf.apps import AppConfig

from .commands import clean
from .tables import SessionsBase

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


APP_CONFIG = AppConfig(
    app_name="session_auth",
    migrations_folder_path=os.path.join(
        CURRENT_DIRECTORY, "piccolo_migrations"
    ),
    table_classes=[SessionsBase],
    migration_dependencies=[],
    commands=[clean],
)
