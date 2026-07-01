from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class KeywordDTO:
    keyword_id: str
    keyword_text: str
    search_cluster: Optional[str] = None
    needs_backfill: bool = False