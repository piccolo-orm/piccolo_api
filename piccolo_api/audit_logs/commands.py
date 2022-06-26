from .tables import AuditLog


async def clean():
    """
    Removes all audit logs.
    """
    print("Removing audit logs ...")
    await AuditLog.delete(force=True).run()
    print("Successfully removed audit logs")
