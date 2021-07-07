from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections import defaultdict
from time import time
import typing as t

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


if t.TYPE_CHECKING:
    from starlette.middleware.base import (
        Request,
        RequestResponseEndpoint,
    )


class RateLimitError(Exception):
    """
    Raised when a client exceeds the request limit. Should be handled
    internally without bleeding out to the rest of the application.
    """

    pass


class RateLimitProvider(metaclass=ABCMeta):
    """
    An abstract base class which all rate limit providers should inherit from.
    """

    @abstractmethod
    def increment(self, identifier: str):
        pass


class InMemoryLimitProvider(RateLimitProvider):
    """
    A very simple rate limiting provider - works fine when running a single
    application instance.

    Time values are given in seconds, rather than a timedelta, for improved
    performance.
    """

    def __init__(
        self,
        timespan: int,
        limit: int = 1000,
        block_duration: t.Optional[int] = None,
    ):
        """
        :param timespan:
            The time in seconds between resetting the number of requests.
            Beware setting it too high, because memory usage will increase.
        :param limit:
            The number of requests in the timespan, before getting blocked.
        :param block_duration:
            If set, the number of seconds before a client is no longer blocked.
            Otherwise, they're only removed when the app is restarted.
        """
        # Maps a client identifier to the number of requests they have made.
        self.request_dict: defaultdict = defaultdict(int)

        self.timespan = timespan
        self.last_reset = time()
        self.limit = limit

        self.blocked: t.Dict[str, float] = {}
        self.block_duration = block_duration

    def _handle_blocked(self):
        raise RateLimitError()

    def is_already_blocked(self, identifier: str) -> bool:
        """
        Check whether the identifier is already blocked from previous
        requests. Remove the identifier if the block has expired.
        """
        blocked_at: t.Optional[float] = self.blocked.get(identifier, None)
        if blocked_at:
            duration = self.block_duration
            if (time() - blocked_at < duration) if duration else True:
                return True
            else:
                del self.blocked[identifier]
                return False
        else:
            return False

    def add_to_blocked(self, identifier: str):
        self.blocked[identifier] = time()

    def increment(self, identifier: str):
        """
        Increment the number of requests with this identifier. If too many
        requests are received during the interval then record them as blocked,
        and reject the request.

        :param identifier:
            An identifier for the client making the request, for example the IP
            address.
        """
        if self.is_already_blocked(identifier):
            self._handle_blocked()

        # Reset the request count if needed.
        now = time()
        if now - self.last_reset > self.timespan:
            self.last_reset = now
            self.request_dict = defaultdict(int)

        self.request_dict[identifier] += 1

        if self.request_dict[identifier] > self.limit:
            self.add_to_blocked(identifier)
            self._handle_blocked()

    def clear_blocked(self):
        """
        Resets the block list.
        """
        self.blocked = {}


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Blocks clients who exceed a given number of requests in a given time
    period.
    """

    def __init__(
        self,
        app: ASGIApp,
        provider: RateLimitProvider = InMemoryLimitProvider(
            limit=1000, timespan=300
        ),
    ):
        super().__init__(app)
        self.rate_limit = provider

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        identifier = request.client.host
        try:
            self.rate_limit.increment(identifier)
        except RateLimitError:
            return Response(content="Too many requests", status_code=429)
        return await call_next(request)
