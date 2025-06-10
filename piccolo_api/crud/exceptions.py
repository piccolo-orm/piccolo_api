import functools
import logging
from collections.abc import Callable, Coroutine
from sqlite3 import IntegrityError

from starlette.responses import JSONResponse

try:
    # We can't be sure that asyncpg is installed, hence why it's in a
    # try / except.
    from asyncpg.exceptions import (
        ForeignKeyViolationError,
        NotNullViolationError,
        UniqueViolationError,
    )
except ImportError:

    class ForeignKeyViolationError(Exception):  # type: ignore
        pass

    class UniqueViolationError(Exception):  # type: ignore
        pass

    class NotNullViolationError(Exception):  # type: ignore
        pass


logger = logging.getLogger(__name__)


class MalformedQuery(Exception):
    """
    Raised when the query is malformed - for example, the column names are
    unrecognised. The exception should be handled internally by PiccoloCRUD,
    and shouldn't bleed out to the wider application.
    """

    pass


def db_exception_handler(func: Callable[..., Coroutine]):
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

    @functools.wraps(func)
    async def inner(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except IntegrityError as exception:
            logger.exception("SQLite integrity error")
            return JSONResponse(
                {"db_error": exception.__str__()},
                status_code=422,
            )
        except UniqueViolationError as exception:
            logger.exception("Asyncpg unique violation")
            return JSONResponse(
                {
                    "db_error": exception.message,
                },
                status_code=422,
            )
        except NotNullViolationError as exception:
            logger.exception("Asyncpg not-null violation")
            return JSONResponse(
                {
                    "db_error": exception.message,
                },
                status_code=422,
            )
        except ForeignKeyViolationError as exception:
            # This is raised when we have an `ON DELETE RESTRICT` constraint
            # on a foreign key, which prevents us from deleting a row if it's
            # referenced by a foreign key.
            logger.exception("Asyncpg foreign key violation")
            return JSONResponse(
                {
                    "db_error": exception.message,
                },
                status_code=422,
            )

    return inner
