from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional

from .models import DEFAULT_PROFILES, TileActivity, TransportName, VideoProfile, VideoProfileName, StreamSession, StreamState, utc_now_iso


class VideoGatewayService:
    """Control-plane Video Gateway: управляет входами RTSP и выдачей WebRTC/HLS профилей."""

    def __init__(self) -> None:
        self._streams: Dict[str, StreamState] = {}
        self._sessions: Dict[str, StreamSession] = {}
        self._lock = threading.RLock()

    def list_profiles(self) -> List[Dict[str, int | str]]:
        return [
            {
                "name": profile.name,
                "width": profile.width,
                "height": profile.height,
                "fps": profile.fps,
                "bitrate_kbps": profile.bitrate_kbps,
            }
            for profile in DEFAULT_PROFILES.values()
        ]

    def list_streams(self) -> List[Dict[str, str | bool]]:
        with self._lock:
            return [stream.to_dict() for stream in self._streams.values()]

    def create_stream(self, stream_id: str, source: str, profile: VideoProfileName = "medium") -> Dict[str, str | bool]:
        stream_id = stream_id.strip()
        source = source.strip()
        self._validate_profile(profile)
        if not stream_id:
            raise ValueError("Поле 'stream_id' обязательно")
        if not source:
            raise ValueError("Поле 'source' обязательно")

        with self._lock:
            if stream_id in self._streams:
                raise ValueError(f"Поток '{stream_id}' уже существует")
            stream = StreamState(stream_id=stream_id, source=source, selected_profile=profile)
            self._streams[stream_id] = stream
            return stream.to_dict()

    def get_stream(self, stream_id: str) -> Optional[Dict[str, str | bool]]:
        with self._lock:
            stream = self._streams.get(stream_id)
            return stream.to_dict() if stream else None

    def set_stream_enabled(self, stream_id: str, enabled: bool) -> Dict[str, str | bool]:
        with self._lock:
            stream = self._must_get_stream(stream_id)
            stream.enabled = enabled
            stream.updated_at = utc_now_iso()
            return stream.to_dict()

    def select_profile(self, stream_id: str, profile: VideoProfileName) -> Dict[str, str | bool]:
        self._validate_profile(profile)
        with self._lock:
            stream = self._must_get_stream(stream_id)
            stream.selected_profile = profile
            stream.updated_at = utc_now_iso()
            return stream.to_dict()

    def pick_profile_for_tile(self, stream_id: str, tile_activity: TileActivity) -> Dict[str, str | bool]:
        if tile_activity not in ("focused", "visible", "background"):
            raise ValueError("tile_activity должен быть: focused|visible|background")
        profile: VideoProfileName = "high" if tile_activity == "focused" else "medium" if tile_activity == "visible" else "low"
        return self.select_profile(stream_id, profile)

    def open_session(self, stream_id: str, transport: TransportName, profile: Optional[VideoProfileName] = None) -> Dict[str, str]:
        if transport not in ("webrtc", "hls"):
            raise ValueError("transport должен быть: webrtc|hls")

        with self._lock:
            stream = self._must_get_stream(stream_id)
            if not stream.enabled:
                raise ValueError(f"Поток '{stream_id}' отключен")

            effective_profile: VideoProfileName = profile or stream.selected_profile
            self._validate_profile(effective_profile)
            session_id = str(uuid.uuid4())
            if transport == "webrtc":
                url = f"webrtc://gateway/{stream_id}?profile={effective_profile}&session_id={session_id}"
            else:
                url = f"/hls/{stream_id}/{effective_profile}/index.m3u8"

            session = StreamSession(
                session_id=session_id,
                stream_id=stream_id,
                transport=transport,
                profile=effective_profile,
                url=url,
            )
            self._sessions[session_id] = session
            return session.to_dict()

    def get_profile(self, profile: VideoProfileName) -> VideoProfile:
        self._validate_profile(profile)
        return DEFAULT_PROFILES[profile]

    def health(self) -> Dict[str, int | str]:
        with self._lock:
            enabled = sum(1 for stream in self._streams.values() if stream.enabled)
            return {
                "status": "ok",
                "streams_total": len(self._streams),
                "streams_enabled": enabled,
                "sessions_total": len(self._sessions),
                "timestamp_utc": utc_now_iso(),
            }

    def metrics(self) -> Dict[str, int | str]:
        with self._lock:
            by_transport = {"webrtc": 0, "hls": 0}
            by_profile = {"high": 0, "medium": 0, "low": 0}
            for session in self._sessions.values():
                by_transport[session.transport] += 1
                by_profile[session.profile] += 1
            return {
                "streams_total": len(self._streams),
                "sessions_total": len(self._sessions),
                "sessions_webrtc": by_transport["webrtc"],
                "sessions_hls": by_transport["hls"],
                "sessions_high": by_profile["high"],
                "sessions_medium": by_profile["medium"],
                "sessions_low": by_profile["low"],
                "timestamp_utc": utc_now_iso(),
            }

    def _validate_profile(self, profile: str) -> None:
        if profile not in DEFAULT_PROFILES:
            raise ValueError("profile должен быть: high|medium|low")

    def _must_get_stream(self, stream_id: str) -> StreamState:
        stream = self._streams.get(stream_id)
        if stream is None:
            raise KeyError(f"Поток '{stream_id}' не найден")
        return stream
