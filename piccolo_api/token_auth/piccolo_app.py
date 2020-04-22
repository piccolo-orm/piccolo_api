import os

from piccolo.conf.apps import AppConfig
from .tables import TokenAuth


CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


APP_CONFIG = AppConfig(
    app_name="token_auth",
    migrations_folder_path=os.path.join(
        CURRENT_DIRECTORY, "piccolo_migrations"
    ),
    table_classes=[TokenAuth],
    migration_dependencies=["piccolo.apps.user.piccolo_app"],
)
