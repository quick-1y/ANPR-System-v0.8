from __future__ import annotations

import threading
import uuid
from collections import deque
from typing import Deque, Dict, List, Optional

from .models import ANPREvent, ChannelTelemetry, utc_now_iso


class EventTelemetryService:
    """Сервис событий ANPR и телеметрии каналов для web-UI/Event layer."""

    def __init__(self, event_buffer_size: int = 2000) -> None:
        self._events: Deque[ANPREvent] = deque(maxlen=event_buffer_size)
        self._channel_telemetry: Dict[str, ChannelTelemetry] = {}
        self._subscribers: Dict[str, int] = {}
        self._alert_rules = {
            "reconnects_warn": 3,
            "timeouts_warn": 3,
            "latency_warn_ms": 500.0,
        }
        self._lock = threading.RLock()

    def subscribe(self) -> Dict[str, object]:
        with self._lock:
            subscriber_id = str(uuid.uuid4())
            self._subscribers[subscriber_id] = len(self._events)
            return {
                "subscriber_id": subscriber_id,
                "cursor": self._subscribers[subscriber_id],
                "timestamp_utc": utc_now_iso(),
            }

    def publish_event(
        self,
        channel_id: str,
        plate: str,
        confidence: float,
        country: Optional[str] = None,
        direction: Optional[str] = None,
        frame_url: Optional[str] = None,
        plate_url: Optional[str] = None,
    ) -> Dict[str, object]:
        if not channel_id.strip():
            raise ValueError("Поле 'channel_id' обязательно")
        if not plate.strip():
            raise ValueError("Поле 'plate' обязательно")

        with self._lock:
            event = ANPREvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=utc_now_iso(),
                channel_id=channel_id,
                plate=plate,
                confidence=float(confidence),
                country=country,
                direction=direction,
                frame_url=frame_url,
                plate_url=plate_url,
            )
            self._events.append(event)
            return event.to_dict()

    def poll_events(self, subscriber_id: str, limit: int = 100) -> Dict[str, object]:
        if limit <= 0:
            raise ValueError("limit должен быть > 0")

        with self._lock:
            if subscriber_id not in self._subscribers:
                raise KeyError(f"Подписчик '{subscriber_id}' не найден")

            cursor = self._subscribers[subscriber_id]
            events_list = list(self._events)
            total = len(events_list)

            if cursor > total:
                cursor = total

            new_events = events_list[cursor : min(total, cursor + limit)]
            next_cursor = cursor + len(new_events)
            self._subscribers[subscriber_id] = next_cursor

            return {
                "subscriber_id": subscriber_id,
                "cursor": next_cursor,
                "items": [event.to_dict() for event in new_events],
                "timestamp_utc": utc_now_iso(),
            }

    def update_channel_telemetry(
        self,
        channel_id: str,
        fps: Optional[float] = None,
        latency_ms: Optional[float] = None,
        reconnects: Optional[int] = None,
        timeouts: Optional[int] = None,
        empty_frames: Optional[int] = None,
    ) -> Dict[str, object]:
        if not channel_id.strip():
            raise ValueError("Поле 'channel_id' обязательно")

        with self._lock:
            telemetry = self._channel_telemetry.get(channel_id) or ChannelTelemetry(channel_id=channel_id)
            if fps is not None:
                telemetry.fps = float(fps)
            if latency_ms is not None:
                telemetry.latency_ms = float(latency_ms)
            if reconnects is not None:
                telemetry.reconnects = int(reconnects)
            if timeouts is not None:
                telemetry.timeouts = int(timeouts)
            if empty_frames is not None:
                telemetry.empty_frames = int(empty_frames)

            telemetry.status = self._resolve_status(telemetry)
            telemetry.updated_at = utc_now_iso()
            self._channel_telemetry[channel_id] = telemetry
            return telemetry.to_dict()

    def list_channel_telemetry(self) -> Dict[str, object]:
        with self._lock:
            return {
                "items": [item.to_dict() for item in self._channel_telemetry.values()],
                "timestamp_utc": utc_now_iso(),
            }

    def alerts(self) -> Dict[str, object]:
        with self._lock:
            items: List[Dict[str, object]] = []
            for telemetry in self._channel_telemetry.values():
                if telemetry.reconnects >= self._alert_rules["reconnects_warn"]:
                    items.append(
                        {
                            "channel_id": telemetry.channel_id,
                            "kind": "reconnect_warn",
                            "value": telemetry.reconnects,
                            "threshold": self._alert_rules["reconnects_warn"],
                        }
                    )
                if telemetry.timeouts >= self._alert_rules["timeouts_warn"]:
                    items.append(
                        {
                            "channel_id": telemetry.channel_id,
                            "kind": "timeout_warn",
                            "value": telemetry.timeouts,
                            "threshold": self._alert_rules["timeouts_warn"],
                        }
                    )
                if telemetry.latency_ms >= self._alert_rules["latency_warn_ms"]:
                    items.append(
                        {
                            "channel_id": telemetry.channel_id,
                            "kind": "latency_warn",
                            "value": telemetry.latency_ms,
                            "threshold": self._alert_rules["latency_warn_ms"],
                        }
                    )
            return {"items": items, "timestamp_utc": utc_now_iso()}

    def health(self) -> Dict[str, object]:
        with self._lock:
            degraded = sum(1 for t in self._channel_telemetry.values() if t.status != "healthy")
            return {
                "status": "ok",
                "channels_total": len(self._channel_telemetry),
                "channels_degraded": degraded,
                "events_buffered": len(self._events),
                "subscribers": len(self._subscribers),
                "timestamp_utc": utc_now_iso(),
            }

    def metrics(self) -> Dict[str, object]:
        with self._lock:
            return {
                "channels_total": len(self._channel_telemetry),
                "events_buffered": len(self._events),
                "subscribers": len(self._subscribers),
                "alerts_total": len(self.alerts()["items"]),
                "timestamp_utc": utc_now_iso(),
            }

    def _resolve_status(self, telemetry: ChannelTelemetry) -> str:
        if telemetry.timeouts >= self._alert_rules["timeouts_warn"] * 2:
            return "offline"
        if (
            telemetry.reconnects >= self._alert_rules["reconnects_warn"]
            or telemetry.timeouts >= self._alert_rules["timeouts_warn"]
            or telemetry.latency_ms >= self._alert_rules["latency_warn_ms"]
        ):
            return "degraded"
        return "healthy"
