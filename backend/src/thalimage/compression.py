"""Gzip the responses worth compressing.

JSON listings repeat their keys on every item and shrink several times over;
images and video are already compressed, and their Range responses (206) give
offsets into the file's own bytes, which a compressed body would not match.
So only text-like content types are compressed, never partial content.
Server-sent events stay uncompressed too (Starlette excludes them), as a
gzip stream would hold events back until its buffer fills.
"""

from starlette.datastructures import Headers
from starlette.middleware.gzip import GZipMiddleware, GZipResponder, IdentityResponder
from starlette.types import Message, Receive, Scope, Send

COMPRESSIBLE_TYPES = ("text/", "application/json", "application/javascript", "image/svg+xml")


class _TextGZipResponder(GZipResponder):
    async def send_with_compression(self, message: Message) -> None:
        await super().send_with_compression(message)
        if message["type"] == "http.response.start":
            # The response start is only held at this point; marking the
            # response excluded makes its body pass through unchanged.
            content_type = Headers(raw=message["headers"]).get("content-type", "")
            if message["status"] == 206 or not content_type.startswith(COMPRESSIBLE_TYPES):
                self.content_type_is_excluded = True


class TextCompression(GZipMiddleware):
    """Starlette's GZipMiddleware, limited to text-like, complete responses."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or "gzip" not in Headers(scope=scope).get("Accept-Encoding", ""):
            await self.app(scope, receive, send)
            return
        responder: IdentityResponder = _TextGZipResponder(
            self.app, self.minimum_size, compresslevel=self.compresslevel
        )
        await responder(scope, receive, send)
