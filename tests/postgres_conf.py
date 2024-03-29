import os

from piccolo.engine.postgres import PostgresEngine

DB = PostgresEngine(
    config={
        "host": os.environ.get("PG_HOST", "localhost"),
        "port": os.environ.get("PG_PORT", "5432"),
        "user": os.environ.get("PG_USER", "postgres"),
        "password": os.environ.get("PG_PASSWORD", ""),
        "database": os.environ.get("PG_DATABASE", "piccolo_api"),
    }
)
