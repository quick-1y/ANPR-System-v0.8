from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Literal

ChannelStatus = Literal["stopped", "running", "error"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChannelQueueStats:
    queued_jobs: int = 0
    processed_jobs: int = 0
    failed_jobs: int = 0


@dataclass
class ChannelState:
    channel_id: str
    name: str
    source: str
    status: ChannelStatus = "stopped"
    roi: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    lists: Dict[str, Any] = field(default_factory=dict)
    queue: ChannelQueueStats = field(default_factory=ChannelQueueStats)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["queue"] = asdict(self.queue)
        return payload
