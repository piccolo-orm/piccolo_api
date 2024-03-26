"""
Used for serving the example session app, so we can manually test it.

Run it from the root of the project using `python -m tests.serve`.
"""

import os

import uvicorn

from .session_auth.test_session import (  # type: ignore
    APP,
    BaseUser,
    SessionsBase,
)

if __name__ == "__main__":
    os.environ["PICCOLO_CONF"] = "tests.sqlite_conf"

    BaseUser.create_table(if_not_exists=True).run_sync()
    SessionsBase.create_table(if_not_exists=True).run_sync()

    if not BaseUser.exists().where(BaseUser.username == "Bob"):
        BaseUser(username="bob", password="bob123").save().run_sync()

    uvicorn.run(APP, port=8999)
