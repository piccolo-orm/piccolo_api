import asyncio
import typing as t


def run_sync(coroutine: t.Coroutine):
    """
    Run async test sync
    """
    loop = asyncio.new_event_loop()
    return loop.run_until_complete(coroutine)
