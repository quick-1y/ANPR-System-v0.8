from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse

from .service import DataLayerService


def _read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    body = handler.rfile.read(length)
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


class DataLayerRequestHandler(BaseHTTPRequestHandler):
    service = DataLayerService()

    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_exception(self, exc: Exception) -> None:
        if isinstance(exc, ValueError):
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "internal_error", "details": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/v1/data/health":
                self._send_json(self.service.health())
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            payload = _read_json(self)
            if parsed.path == "/api/v1/data/retention":
                result = self.service.retention_delete_older_than_days(int(payload.get("days", 30)))
                self._send_json(result)
                return
            if parsed.path == "/api/v1/data/export/json":
                result = self.service.export_events_json(
                    output_path=str(payload.get("output_path", "exports/events.json")),
                    limit=int(payload.get("limit", 1000)),
                )
                self._send_json(result)
                return
            if parsed.path == "/api/v1/data/export/csv":
                result = self.service.export_events_csv(
                    output_path=str(payload.get("output_path", "exports/events.csv")),
                    limit=int(payload.get("limit", 1000)),
                )
                self._send_json(result)
                return
            if parsed.path == "/api/v1/data/media/cleanup":
                self._send_json(self.service.media_rotation_cleanup())
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover
            self._handle_exception(exc)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def run_server(host: str = "127.0.0.1", port: int = 8120) -> None:
    server = ThreadingHTTPServer((host, port), DataLayerRequestHandler)
    print(f"Data Layer API listening on http://{host}:{port}")
    server.serve_forever()
