from time import sleep
from unittest import TestCase

from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.routing import Route, Router
from starlette.testclient import TestClient

from piccolo_api.rate_limiting.middleware import (
    InMemoryLimitProvider,
    RateLimitingMiddleware,
)


class Endpoint(HTTPEndpoint):
    async def get(self, request):
        return JSONResponse({"message": "ok"})


class TestMiddleware(TestCase):
    def test_limit(self):
        """
        Make sure a request is rejected if the client has exceeded the limit.
        """
        app = RateLimitingMiddleware(
            Router([Route("/", Endpoint)]),
            InMemoryLimitProvider(limit=5, timespan=1, block_duration=1),
        )

        client = TestClient(app)

        successful = 0
        for i in range(20):
            response = client.get("/")
            if response.status_code == 429:
                break
            else:
                successful += 1

        self.assertEqual(successful, 5)

        # After the 'block_duration' has expired, requests should be allowed
        # again.
        sleep(1.1)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_memory_usage(self):
        """
        Make sure the memory used doesn't continue to increase over time (it
        should reset regularly at intervals of 'timespan' seconds).
        """
        provider = InMemoryLimitProvider(
            limit=10, timespan=1, block_duration=1
        )
        for i in range(100):
            provider.increment(str(i))

        self.assertEqual(len(provider.request_dict.keys()), 100)

        sleep(1)

        # This should cause a reset, as the timespan has elapsed:
        provider.increment("1234")
        self.assertEqual(len(provider.request_dict.keys()), 1)
