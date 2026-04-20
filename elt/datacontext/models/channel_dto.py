from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ChannelDTO:
    channel_id: str
    channel_name: str
    is_active: bool = True
    is_historically_scanned: bool = False
    channel_url: Optional[str] = None
    channel_handle: Optional[str] = None
    subscriber_count: Optional[int] = None
    historical_scan_completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        def _fmt(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "channel_url": self.channel_url,
            "channel_handle": self.channel_handle,
            "subscriber_count": self.subscriber_count,
            "is_active": self.is_active,
            "is_historically_scanned": self.is_historically_scanned,
            "historical_scan_completed_at": _fmt(self.historical_scan_completed_at),
            "created_at": _fmt(self.created_at),
            "last_updated_at": _fmt(self.last_updated_at),
        }