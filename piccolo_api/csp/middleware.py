from __future__ import annotations
from dataclasses import dataclass
from functools import wraps
import typing as t

if t.TYPE_CHECKING:
    from starlette.types import ASGIApp, Send, Receive, Scope, Message


@dataclass
class CSPConfig:
    report_uri: t.Optional[bytes] = None


class CSPMiddleware:
    """
    Adds Content Security Policy headers to the response.

    Might consider replacing with: https://secure.readthedocs.io/en/latest/
    """

    def __init__(self, app: ASGIApp, config: CSPConfig = CSPConfig()):
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        @wraps(send)
        async def wrapped_send(message: Message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                header_value = b"default-src 'self'"
                if self.config.report_uri:
                    header_value = (
                        header_value
                        + b"; report-uri "
                        + self.config.report_uri
                    )
                headers.append([b"Content-Security-Policy", header_value])
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, wrapped_send)
