from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

from .service import ANPRCoreService


def _read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    body = handler.rfile.read(length)
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def _parse_channel_path(path: str) -> Tuple[str | None, str | None]:
    parts = [part for part in path.split("/") if part]
    # /api/v1/channels/{id}/action
    if len(parts) < 4:
        return None, None
    if parts[0:3] != ["api", "v1", "channels"]:
        return None, None
    channel_id = parts[3]
    action = parts[4] if len(parts) >= 5 else None
    return channel_id, action


class ANPRCoreRequestHandler(BaseHTTPRequestHandler):
    service = ANPRCoreService()

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
        try:
            if parsed.path == "/api/v1/health":
                self._send_json(self.service.health())
                return
            if parsed.path == "/api/v1/metrics":
                self._send_json(self.service.metrics())
                return
            if parsed.path == "/api/v1/channels":
                self._send_json({"items": self.service.list_channels()})
                return

            channel_id, action = _parse_channel_path(parsed.path)
            if channel_id and action is None:
                channel = self.service.get_channel(channel_id)
                if channel is None:
                    self._send_json({"error": f"Канал '{channel_id}' не найден"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json(channel)
                return

            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/v1/channels":
                payload = _read_json(self)
                created = self.service.create_channel(payload)
                self._send_json(created, status=HTTPStatus.CREATED)
                return

            channel_id, action = _parse_channel_path(parsed.path)
            if channel_id and action in {"start", "stop", "restart"}:
                if action == "start":
                    payload = self.service.start_channel(channel_id)
                elif action == "stop":
                    payload = self.service.stop_channel(channel_id)
                else:
                    payload = self.service.restart_channel(channel_id)
                self._send_json(payload)
                return

            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def do_PATCH(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            channel_id, action = _parse_channel_path(parsed.path)
            if channel_id and action is None:
                payload = _read_json(self)
                updated = self.service.update_channel(channel_id, payload)
                self._send_json(updated)
                return

            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            channel_id, action = _parse_channel_path(parsed.path)
            payload = _read_json(self)
            if channel_id and action == "roi":
                self._send_json(self.service.update_roi(channel_id, payload))
                return
            if channel_id and action == "filters":
                self._send_json(self.service.update_filters(channel_id, payload))
                return
            if channel_id and action == "lists":
                self._send_json(self.service.update_lists(channel_id, payload))
                return

            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), ANPRCoreRequestHandler)
    print(f"ANPR Core API listening on http://{host}:{port}")
    server.serve_forever()
