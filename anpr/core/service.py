from __future__ import annotations

import threading
from dataclasses import replace
from typing import Any, Dict, List, Optional

from .models import ChannelQueueStats, ChannelState, utc_now_iso


class ANPRCoreService:
    """Headless управление каналами для будущего backend ANPR Core Service."""

    def __init__(self) -> None:
        self._channels: Dict[str, ChannelState] = {}
        self._lock = threading.RLock()

    def list_channels(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [channel.to_dict() for channel in self._channels.values()]

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            channel = self._channels.get(channel_id)
            return channel.to_dict() if channel else None

    def create_channel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        channel_id = str(payload.get("id", "")).strip()
        name = str(payload.get("name", "")).strip()
        source = str(payload.get("source", "")).strip()
        if not channel_id:
            raise ValueError("Поле 'id' обязательно")
        if not name:
            raise ValueError("Поле 'name' обязательно")
        if not source:
            raise ValueError("Поле 'source' обязательно")

        with self._lock:
            if channel_id in self._channels:
                raise ValueError(f"Канал '{channel_id}' уже существует")

            channel = ChannelState(
                channel_id=channel_id,
                name=name,
                source=source,
                roi=dict(payload.get("roi") or {}),
                filters=dict(payload.get("filters") or {}),
                lists=dict(payload.get("lists") or {}),
            )
            self._channels[channel_id] = channel
            return channel.to_dict()

    def update_channel(self, channel_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            channel = self._must_get(channel_id)
            updated = replace(
                channel,
                name=str(payload.get("name", channel.name)).strip() or channel.name,
                source=str(payload.get("source", channel.source)).strip() or channel.source,
                updated_at=utc_now_iso(),
            )
            self._channels[channel_id] = updated
            return updated.to_dict()

    def update_roi(self, channel_id: str, roi: Dict[str, Any]) -> Dict[str, Any]:
        return self._patch_channel_dict(channel_id, "roi", roi)

    def update_filters(self, channel_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        return self._patch_channel_dict(channel_id, "filters", filters)

    def update_lists(self, channel_id: str, lists: Dict[str, Any]) -> Dict[str, Any]:
        return self._patch_channel_dict(channel_id, "lists", lists)

    def start_channel(self, channel_id: str) -> Dict[str, Any]:
        return self._set_status(channel_id, "running")

    def stop_channel(self, channel_id: str) -> Dict[str, Any]:
        return self._set_status(channel_id, "stopped")

    def restart_channel(self, channel_id: str) -> Dict[str, Any]:
        with self._lock:
            channel = self._must_get(channel_id)
            channel.status = "stopped"
            channel.status = "running"
            channel.updated_at = utc_now_iso()
            return channel.to_dict()

    def queue_job(self, channel_id: str) -> Dict[str, Any]:
        with self._lock:
            channel = self._must_get(channel_id)
            channel.queue.queued_jobs += 1
            channel.updated_at = utc_now_iso()
            return channel.to_dict()

    def complete_job(self, channel_id: str, ok: bool = True) -> Dict[str, Any]:
        with self._lock:
            channel = self._must_get(channel_id)
            if channel.queue.queued_jobs > 0:
                channel.queue.queued_jobs -= 1
            if ok:
                channel.queue.processed_jobs += 1
            else:
                channel.queue.failed_jobs += 1
            channel.updated_at = utc_now_iso()
            return channel.to_dict()

    def health(self) -> Dict[str, Any]:
        with self._lock:
            running = sum(1 for channel in self._channels.values() if channel.status == "running")
            return {
                "status": "ok",
                "channels_total": len(self._channels),
                "channels_running": running,
                "timestamp_utc": utc_now_iso(),
            }

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            queued = 0
            processed = 0
            failed = 0
            for channel in self._channels.values():
                stats: ChannelQueueStats = channel.queue
                queued += stats.queued_jobs
                processed += stats.processed_jobs
                failed += stats.failed_jobs
            return {
                "channels_total": len(self._channels),
                "jobs_queued": queued,
                "jobs_processed": processed,
                "jobs_failed": failed,
                "timestamp_utc": utc_now_iso(),
            }

    def _set_status(self, channel_id: str, status: str) -> Dict[str, Any]:
        with self._lock:
            channel = self._must_get(channel_id)
            channel.status = status  # type: ignore[assignment]
            channel.updated_at = utc_now_iso()
            return channel.to_dict()

    def _patch_channel_dict(self, channel_id: str, attr: str, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("Тело запроса должно быть JSON-объектом")
        with self._lock:
            channel = self._must_get(channel_id)
            setattr(channel, attr, dict(value))
            channel.updated_at = utc_now_iso()
            return channel.to_dict()

    def _must_get(self, channel_id: str) -> ChannelState:
        channel = self._channels.get(channel_id)
        if channel is None:
            raise KeyError(f"Канал '{channel_id}' не найден")
        return channel
