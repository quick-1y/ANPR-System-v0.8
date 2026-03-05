from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, Literal

VideoProfileName = Literal["high", "medium", "low"]
TransportName = Literal["webrtc", "hls"]
TileActivity = Literal["focused", "visible", "background"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class VideoProfile:
    name: VideoProfileName
    width: int
    height: int
    fps: int
    bitrate_kbps: int


DEFAULT_PROFILES: Dict[VideoProfileName, VideoProfile] = {
    "high": VideoProfile(name="high", width=1920, height=1080, fps=25, bitrate_kbps=3500),
    "medium": VideoProfile(name="medium", width=1280, height=720, fps=15, bitrate_kbps=1800),
    "low": VideoProfile(name="low", width=854, height=480, fps=8, bitrate_kbps=900),
}


@dataclass
class StreamSession:
    session_id: str
    stream_id: str
    transport: TransportName
    profile: VideoProfileName
    url: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class StreamState:
    stream_id: str
    source: str
    enabled: bool = True
    selected_profile: VideoProfileName = "medium"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, str | bool]:
        return asdict(self)
