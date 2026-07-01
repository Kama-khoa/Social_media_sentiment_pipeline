from __future__ import annotations

from unittest.mock import patch

import pytest

from elt.extract.helpers.ytdlp_session_pool import (
    YtdlpFetchError,
    YtdlpRateLimitError,
    YtdlpSessionPool,
)


def test_rotates_to_next_session_after_rate_limit():
    pool = YtdlpSessionPool(["session-1.txt", "session-2.txt"])
    used_sessions: list[str | None] = []

    def operation(cookies_path: str | None) -> str:
        used_sessions.append(cookies_path)
        if cookies_path == "session-1.txt":
            raise YtdlpRateLimitError("rate limited")
        return "ok"

    assert pool.execute(operation) == "ok"
    assert used_sessions == ["session-1.txt", "session-2.txt"]


def test_reuses_single_session_after_cooldown():
    pool = YtdlpSessionPool(["session-1.txt"], cooldown_seconds=3600)
    attempts = 0

    def operation(cookies_path: str | None) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise YtdlpRateLimitError("rate limited")
        return "ok"

    with patch(
        "elt.extract.helpers.ytdlp_session_pool.time.monotonic",
        side_effect=[0.0, 0.0, 3600.0],
    ):
        assert pool.execute(operation) == "ok"

    assert attempts == 2


def test_does_not_retry_non_rate_limit_error():
    pool = YtdlpSessionPool(["session-1.txt", "session-2.txt"])

    with pytest.raises(YtdlpFetchError):
        pool.execute(lambda _: (_ for _ in ()).throw(YtdlpFetchError("network")))
