from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse

from .service import VideoGatewayService


def _read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    body = handler.rfile.read(length)
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


class VideoGatewayRequestHandler(BaseHTTPRequestHandler):
    service = VideoGatewayService()

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
        try:
            if path == "/api/v1/video/health":
                self._send_json(self.service.health())
                return
            if path == "/api/v1/video/metrics":
                self._send_json(self.service.metrics())
                return
            if path == "/api/v1/video/profiles":
                self._send_json({"items": self.service.list_profiles()})
                return
            if path == "/api/v1/video/streams":
                self._send_json({"items": self.service.list_streams()})
                return
            parts = [p for p in path.split("/") if p]
            if len(parts) == 5 and parts[:4] == ["api", "v1", "video", "streams"]:
                stream = self.service.get_stream(parts[4])
                if stream is None:
                    self._send_json({"error": f"Поток '{parts[4]}' не найден"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json(stream)
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/v1/video/streams":
                payload = _read_json(self)
                created = self.service.create_stream(
                    stream_id=str(payload.get("stream_id", "")),
                    source=str(payload.get("source", "")),
                    profile=str(payload.get("profile", "medium")),
                )
                self._send_json(created, status=HTTPStatus.CREATED)
                return

            parts = [p for p in path.split("/") if p]
            payload = _read_json(self)

            if len(parts) == 6 and parts[:4] == ["api", "v1", "video", "streams"] and parts[5] == "enable":
                self._send_json(self.service.set_stream_enabled(parts[4], enabled=bool(payload.get("enabled", True))))
                return

            if len(parts) == 6 and parts[:4] == ["api", "v1", "video", "streams"] and parts[5] == "profile":
                self._send_json(self.service.select_profile(parts[4], profile=str(payload.get("profile", "medium"))))
                return

            if len(parts) == 6 and parts[:4] == ["api", "v1", "video", "streams"] and parts[5] == "tile-activity":
                self._send_json(self.service.pick_profile_for_tile(parts[4], tile_activity=str(payload.get("tile_activity", "visible"))))
                return

            if len(parts) == 6 and parts[:4] == ["api", "v1", "video", "streams"] and parts[5] == "session":
                session = self.service.open_session(
                    stream_id=parts[4],
                    transport=str(payload.get("transport", "webrtc")),
                    profile=payload.get("profile"),
                )
                self._send_json(session, status=HTTPStatus.CREATED)
                return

            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def run_server(host: str = "127.0.0.1", port: int = 8090) -> None:
    server = ThreadingHTTPServer((host, port), VideoGatewayRequestHandler)
    print(f"Video Gateway API listening on http://{host}:{port}")
    server.serve_forever()
