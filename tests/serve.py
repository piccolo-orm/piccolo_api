"""
Used for serving the example session app, so we can manually test it.
"""

if __name__ == "__main__":
    import os
    import sys

    import uvicorn

    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    from test_session import APP, Sessions, User, clear_database  # noqa

    clear_database()
    User.create_table().run_sync()
    Sessions.create_table().run_sync()

    User(username="bob", password="bob123").save().run_sync()

    uvicorn.run(APP, port=8999, reload=True)
