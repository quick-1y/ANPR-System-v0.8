from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from .service import EventTelemetryService


def _read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    body = handler.rfile.read(length)
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


class EventTelemetryRequestHandler(BaseHTTPRequestHandler):
    service = EventTelemetryService()

    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _handle_exception(self, exc: Exception) -> None:
        if isinstance(exc, KeyError):
            self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
            return
        if isinstance(exc, ValueError):
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "internal_error", "details": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/api/v1/events/health":
                self._send_json(self.service.health())
                return
            if path == "/api/v1/events/metrics":
                self._send_json(self.service.metrics())
                return
            if path == "/api/v1/events/telemetry":
                self._send_json(self.service.list_channel_telemetry())
                return
            if path == "/api/v1/events/alerts":
                self._send_json(self.service.alerts())
                return
            if path == "/api/v1/events/poll":
                subscriber_id = (query.get("subscriber_id") or [""])[0]
                limit = int((query.get("limit") or ["100"])[0])
                self._send_json(self.service.poll_events(subscriber_id=subscriber_id, limit=limit))
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/v1/events/subscribe":
                self._send_json(self.service.subscribe(), status=HTTPStatus.CREATED)
                return
            if path == "/api/v1/events/publish":
                payload = _read_json(self)
                event = self.service.publish_event(
                    channel_id=str(payload.get("channel_id", "")),
                    plate=str(payload.get("plate", "")),
                    confidence=float(payload.get("confidence", 0.0)),
                    country=payload.get("country"),
                    direction=payload.get("direction"),
                    frame_url=payload.get("frame_url"),
                    plate_url=payload.get("plate_url"),
                )
                self._send_json(event, status=HTTPStatus.CREATED)
                return
            if path == "/api/v1/events/telemetry":
                payload = _read_json(self)
                telemetry = self.service.update_channel_telemetry(
                    channel_id=str(payload.get("channel_id", "")),
                    fps=payload.get("fps"),
                    latency_ms=payload.get("latency_ms"),
                    reconnects=payload.get("reconnects"),
                    timeouts=payload.get("timeouts"),
                    empty_frames=payload.get("empty_frames"),
                )
                self._send_json(telemetry)
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def run_server(host: str = "127.0.0.1", port: int = 8100) -> None:
    server = ThreadingHTTPServer((host, port), EventTelemetryRequestHandler)
    print(f"Event & Telemetry API listening on http://{host}:{port}")
    server.serve_forever()
