import os
import sys

# Modify the path, so piccolo_api is available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def reset_db():
    print("Resetting DB ...")

    from piccolo.apps.user.tables import BaseUser

    from piccolo_api.mfa.authenticator.tables import AuthenticatorSecret
    from piccolo_api.session_auth.tables import SessionsBase

    BaseUser.delete(force=True).run_sync()
    AuthenticatorSecret.delete(force=True).run_sync()
    SessionsBase.delete(force=True).run_sync()


if __name__ == "__main__":

    if "--reset-db" in sys.argv:
        reset_db()

    import uvicorn

    uvicorn.run("app:app", reload=True)
