"""Refuse writes that a browser makes on behalf of another site.

The app has no authentication: anything that can reach it may write. A
page on any other site, opened in a browser on the same network, could
otherwise send it POSTs (a form, or fetch() in no-cors mode) that need no
preflight. Browsers say where a request comes from (Origin, and
Sec-Fetch-Site), so unsafe methods carrying a foreign origin are refused.
Requests with neither header come from scripts and tools, which a page
cannot forge, and pass.
"""

from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _host_matches(host: str, patterns: list[str]) -> bool:
    """TrustedHostMiddleware's rule: exact, "*", or "*.domain" suffix."""
    for pattern in patterns:
        if pattern == "*" or host == pattern:
            return True
        if pattern.startswith("*.") and host.endswith(pattern[1:]):
            return True
    return False


class CrossSiteWriteGuard:
    def __init__(
        self, app: ASGIApp, *, allowed_hosts: list[str], allowed_origins: list[str]
    ) -> None:
        self.app = app
        self.allowed_hosts = allowed_hosts
        self.allowed_origins = {o.rstrip("/") for o in allowed_origins}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in UNSAFE_METHODS:
            if not self._allowed(Headers(scope=scope)):
                response = PlainTextResponse("Cross-site request refused", status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)

    def _allowed(self, headers: Headers) -> bool:
        origin = headers.get("origin")
        if origin is not None and origin.rstrip("/") in self.allowed_origins:
            return True  # an origin the operator opened CORS to
        if headers.get("sec-fetch-site") == "cross-site":
            return False
        if origin is None:
            return True
        parts = urlsplit(origin)
        if not parts.hostname:
            return False  # "null": sandboxed frames, data: URLs
        if parts.netloc == headers.get("host"):
            return True  # same origin
        # A page served under a name the app already answers to.
        return _host_matches(parts.hostname, self.allowed_hosts)
