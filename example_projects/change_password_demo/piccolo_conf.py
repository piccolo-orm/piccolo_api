import os
import sys

from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

# Modify the path, so piccolo_api is available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

DB = PostgresEngine(
    config={
        "database": "piccolo_api_change_password",
        "user": "postgres",
        "password": "",
        "host": "localhost",
        "port": 5432,
    }
)

APP_REGISTRY = AppRegistry(
    apps=[
        "piccolo.apps.user.piccolo_app",
        "piccolo_api.session_auth.piccolo_app",
    ]
)
