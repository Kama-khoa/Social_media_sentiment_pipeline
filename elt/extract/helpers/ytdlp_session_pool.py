from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class YtdlpRateLimitError(Exception):
    pass


class YtdlpFetchError(Exception):
    pass


@dataclass
class _Session:
    cookies_path: str | None
    blocked_until: float = 0.0


class YtdlpSessionPool:
    def __init__(
        self,
        cookies_paths: list[str] | None = None,
        cooldown_seconds: int = 3600,
    ) -> None:
        paths = cookies_paths or [None]
        self._sessions = [_Session(path) for path in paths]
        self._cooldown_seconds = cooldown_seconds
        self._next_index = 0

    def execute(self, operation: Callable[[str | None], T]) -> T:
        while True:
            session = self._acquire()
            try:
                return operation(session.cookies_path)
            except YtdlpRateLimitError:
                session.blocked_until = time.monotonic() + self._cooldown_seconds
                logger.warning(
                    "yt-dlp session %s rate-limited; cooling down for %ds",
                    self._label(session),
                    self._cooldown_seconds,
                )

    def _acquire(self) -> _Session:
        while True:
            now = time.monotonic()
            for offset in range(len(self._sessions)):
                index = (self._next_index + offset) % len(self._sessions)
                session = self._sessions[index]
                if session.blocked_until <= now:
                    self._next_index = (index + 1) % len(self._sessions)
                    return session

            wait_seconds = max(
                0.0,
                min(session.blocked_until for session in self._sessions) - now,
            )
            logger.warning(
                "All yt-dlp sessions are cooling down; waiting %.0fs",
                wait_seconds,
            )
            time.sleep(wait_seconds)

    def _label(self, session: _Session) -> str:
        index = self._sessions.index(session) + 1
        return f"{index}/{len(self._sessions)}"
