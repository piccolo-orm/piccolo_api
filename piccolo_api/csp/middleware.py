from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


@dataclass
class CSPConfig:
    report_uri: Optional[bytes] = None
    default_src: str = "self"


class CSPMiddleware:
    """
    Adds Content Security Policy headers to the response.
    """

    def __init__(self, app: ASGIApp, config: CSPConfig = CSPConfig()):
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        @wraps(send)
        async def wrapped_send(message: Message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                header_value = bytes(
                    f"default-src '{self.config.default_src}'", "utf8"
                )
                if self.config.report_uri:
                    header_value = (
                        header_value
                        + b"; report-uri "
                        + self.config.report_uri
                    )
                headers.append([b"content-security-policy", header_value])
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, wrapped_send)
