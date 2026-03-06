from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


from anpr.infrastructure.logging_manager import get_logger

logger = get_logger(__name__)


@dataclass
class ChannelConfig:
    id: int
    name: str
    source: str
    roi: dict = field(default_factory=dict)
    enabled: bool = True


class ChannelRuntime:
    def __init__(self, config: ChannelConfig, telemetry: "TelemetryService") -> None:
        self.config = config
        self.telemetry = telemetry
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_jpeg: Optional[bytes] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        logger.info("Запуск канала %s", self.config.name)
        import cv2
        from anpr.pipeline.factory import build_components

        pipeline, detector = build_components(best_shots=3, cooldown_seconds=3, min_confidence=0.5)

        while not self._stop_event.is_set():
            cap = cv2.VideoCapture(int(self.config.source) if self.config.source.isnumeric() else self.config.source)
            if not cap.isOpened():
                self.telemetry.set_status(self.config.id, "offline")
                logger.warning("Канал %s недоступен, повтор через 3с", self.config.name)
                time.sleep(3)
                continue

            self.telemetry.set_status(self.config.id, "online")
            frame_counter = 0
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    self.telemetry.increment_reconnect(self.config.id)
                    self.telemetry.set_status(self.config.id, "reconnecting")
                    break

                frame_counter += 1
                if frame_counter % 2 == 0:
                    detections = detector.detect(frame)
                    results = pipeline.process_frame(frame, detections)
                    for result in results:
                        plate = result.get("text", "")
                        if plate:
                            self.telemetry.push_event(
                                {
                                    "channel_id": self.config.id,
                                    "channel": self.config.name,
                                    "plate": plate,
                                    "confidence": float(result.get("confidence", 0.0)),
                                    "direction": result.get("direction", "UNKNOWN"),
                                    "timestamp": time.time(),
                                }
                            )

                ok_enc, jpg = cv2.imencode(".jpg", frame)
                if ok_enc:
                    self.last_jpeg = jpg.tobytes()
                self.telemetry.touch_frame(self.config.id)

            cap.release()
            time.sleep(0.5)


class TelemetryService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._channel_stats: Dict[int, dict] = {}
        self._events: List[dict] = []

    def ensure_channel(self, channel_id: int) -> None:
        with self._lock:
            self._channel_stats.setdefault(channel_id, {"status": "created", "last_frame_ts": 0.0, "reconnects": 0})

    def set_status(self, channel_id: int, status: str) -> None:
        with self._lock:
            self.ensure_channel(channel_id)
            self._channel_stats[channel_id]["status"] = status

    def touch_frame(self, channel_id: int) -> None:
        with self._lock:
            self.ensure_channel(channel_id)
            self._channel_stats[channel_id]["last_frame_ts"] = time.time()

    def increment_reconnect(self, channel_id: int) -> None:
        with self._lock:
            self.ensure_channel(channel_id)
            self._channel_stats[channel_id]["reconnects"] += 1

    def push_event(self, event: dict) -> None:
        with self._lock:
            self._events.append(event)
            del self._events[:-200]

    def pop_events(self) -> List[dict]:
        with self._lock:
            events = list(self._events)
            self._events.clear()
            return events

    def snapshot(self) -> Dict[int, dict]:
        with self._lock:
            return {cid: dict(stats) for cid, stats in self._channel_stats.items()}


class ChannelService:
    def __init__(self) -> None:
        self.telemetry = TelemetryService()
        self._channels: Dict[int, ChannelConfig] = {}
        self._runtimes: Dict[int, ChannelRuntime] = {}
        self._next_id = 1

    def list_channels(self) -> List[ChannelConfig]:
        return list(self._channels.values())

    def add_channel(self, name: str, source: str, roi: Optional[dict] = None) -> ChannelConfig:
        channel = ChannelConfig(id=self._next_id, name=name, source=source, roi=roi or {})
        self._next_id += 1
        self._channels[channel.id] = channel
        self.telemetry.ensure_channel(channel.id)
        runtime = ChannelRuntime(channel, self.telemetry)
        self._runtimes[channel.id] = runtime
        runtime.start()
        return channel

    def remove_channel(self, channel_id: int) -> bool:
        runtime = self._runtimes.pop(channel_id, None)
        if runtime:
            runtime.stop()
        removed = self._channels.pop(channel_id, None)
        return removed is not None

    def update_roi(self, channel_id: int, roi: dict) -> bool:
        channel = self._channels.get(channel_id)
        if not channel:
            return False
        channel.roi = roi
        return True

    def get_frame(self, channel_id: int) -> Optional[bytes]:
        runtime = self._runtimes.get(channel_id)
        if not runtime:
            return None
        return runtime.last_jpeg

    def stop(self) -> None:
        for runtime in list(self._runtimes.values()):
            runtime.stop()
