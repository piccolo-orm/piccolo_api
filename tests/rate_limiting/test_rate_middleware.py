from time import sleep
from unittest import TestCase

from piccolo_api.rate_limiting.middleware import (
    RateLimitingMiddleware,
    InMemoryLimitProvider,
)
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.routing import Route, Router
from starlette.testclient import TestClient


class Endpoint(HTTPEndpoint):
    async def get(self, request):
        return JSONResponse({"message": "ok"})


app = RateLimitingMiddleware(
    Router([Route("/", Endpoint)]),
    InMemoryLimitProvider(limit=10, timespan=1, block_duration=1),
)


class TestMiddleware(TestCase):
    def test_limit(self):
        client = TestClient(app)

        successful = 0
        for i in range(20):
            response = client.get("/")
            if response.status_code == 429:
                break
            else:
                successful += 1

        self.assertTrue(successful == 10)

        # After the 'block_duration' has expired, requests should be allowed
        # again.
        sleep(1)
        response = client.get("/")
        self.assertTrue(response.status_code == 200)
