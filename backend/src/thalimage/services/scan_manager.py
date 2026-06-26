"""Manages background scan state and progress notifications."""

import asyncio
import threading
from typing import Optional

from pydantic import BaseModel


class ScanProgress(BaseModel):
    source_id: int
    phase: str = "idle"  # idle, discovering, processing, complete, error
    current: int = 0
    total: int = 0
    added: int = 0
    skipped: int = 0
    errors: int = 0
    message: str = ""


class ScanManager:
    """Tracks scan state per source, notifies SSE subscribers."""

    def __init__(self, *, concurrent: bool = True) -> None:
        self._concurrent = concurrent
        self._progress: dict[int, ScanProgress] = {}
        self._events: dict[int, asyncio.Event] = {}
        self._global_lock = threading.Lock()

    def is_running(self, source_id: int) -> bool:
        p = self._progress.get(source_id)
        return p is not None and p.phase in ("discovering", "processing")

    def any_running(self) -> bool:
        return any(self.is_running(sid) for sid in self._progress)

    def can_start(self, source_id: int) -> bool:
        if self.is_running(source_id):
            return False
        if not self._concurrent and self.any_running():
            return False
        return True

    def start(self, source_id: int) -> ScanProgress:
        progress = ScanProgress(source_id=source_id, phase="discovering")
        self._progress[source_id] = progress
        self._events[source_id] = asyncio.Event()
        return progress

    def update(self, source_id: int, **kwargs: object) -> None:
        p = self._progress.get(source_id)
        if p is None:
            return
        for key, value in kwargs.items():
            if hasattr(p, key):
                setattr(p, key, value)
        event = self._events.get(source_id)
        if event:
            event.set()

    def complete(self, source_id: int, **kwargs: object) -> None:
        self.update(source_id, phase="complete", **kwargs)

    def fail(self, source_id: int, message: str = "") -> None:
        self.update(source_id, phase="error", message=message)

    def get_progress(self, source_id: int) -> Optional[ScanProgress]:
        return self._progress.get(source_id)

    async def wait_for_update(self, source_id: int, timeout: float = 5.0) -> Optional[ScanProgress]:
        """Wait for a progress update, returning the current state."""
        event = self._events.get(source_id)
        if event is None:
            return None
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            event.clear()
        except asyncio.TimeoutError:
            pass
        return self._progress.get(source_id)
