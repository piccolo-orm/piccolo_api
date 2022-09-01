import typing as t
from sqlite3 import IntegrityError

from starlette.responses import JSONResponse

try:
    # We can't be sure that asyncpg is installed, hence why it's in a
    # try / except.
    from asyncpg.exceptions import UniqueViolationError
except ImportError:

    class UniqueViolationError(Exception):  # type: ignore
        pass


class MalformedQuery(Exception):
    """
    Raised when the query is malformed - for example, the column names are
    unrecognised. The exception should be handled internally by PiccoloCRUD,
    and shouldn't bleed out to the wider application.
    """

    pass


def db_exception_handler(func: t.Callable[..., t.Coroutine]):
    """
    A decorator which wraps an endpoint, and converts database exceptions
    into HTTP responses.

    Eventually we will add generic database exceptions to Piccolo, so each
    database adapter raises the same exceptions.

    For now though, we handle the exceptions from each database adapter.

    It's very important that we catch unique constraint errors, as these are
    very commmon, and make a poor user experience if the user just sees a
    generic 500 error instead of a useful message like 'Field X is not unique'.

    https://github.com/piccolo-orm/piccolo_admin/issues/167

    """

    async def inner(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except IntegrityError as exception:
            return JSONResponse(
                {"message": exception.__str__()}, status_code=422
            )
        except UniqueViolationError as exception:
            return JSONResponse(
                {"message": exception.message}, status_code=422
            )

    return inner
