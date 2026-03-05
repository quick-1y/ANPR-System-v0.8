from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, Literal, Optional

ChannelStatus = Literal["healthy", "degraded", "offline"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ANPREvent:
    event_id: str
    timestamp_utc: str
    channel_id: str
    plate: str
    confidence: float
    country: Optional[str] = None
    direction: Optional[str] = None
    frame_url: Optional[str] = None
    plate_url: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ChannelTelemetry:
    channel_id: str
    fps: float = 0.0
    latency_ms: float = 0.0
    reconnects: int = 0
    timeouts: int = 0
    empty_frames: int = 0
    status: ChannelStatus = "healthy"
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
