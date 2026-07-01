from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from elt.repositories.quota_repository import QuotaRepository


def test_get_today_used_by_bucket_filters_by_created_at_date():
    client = MagicMock()
    query_job = MagicMock()
    query_job.result.return_value = []
    client.query.return_value = query_job

    QuotaRepository(client, "project", "dataset").get_today_used_by_bucket(date(2026, 6, 3))

    query = client.query.call_args[0][0]
    assert "DATE(created_at) = @today" in query
    assert "log_date = @today" not in query
