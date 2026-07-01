from __future__ import annotations

from pathlib import Path


def test_api_comment_backfill_state_schema_has_last_page_token():
    path = Path("schema/layer_1_raw/init_api_comment_tables.py")
    assert '"last_page_token"' in path.read_text(encoding="utf-8")
