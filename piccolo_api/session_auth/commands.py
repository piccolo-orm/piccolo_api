from datetime import datetime

from .tables import SessionsBase


async def clean():
    """
    Removes any sessions from the table which have expired.
    """
    print("Removing old sessions ...")
    now = datetime.now()
    await SessionsBase.delete().where(SessionsBase.expiry_date < now).run()
    print("Successfully removed old sessions")
