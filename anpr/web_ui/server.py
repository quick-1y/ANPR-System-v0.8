from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict


STATIC_DIR = Path(__file__).resolve().parent / "static"


def build_runtime_config(core_base_url: str, video_base_url: str, events_base_url: str) -> Dict[str, str]:
    return {
        "core_base_url": core_base_url.rstrip("/"),
        "video_base_url": video_base_url.rstrip("/"),
        "events_base_url": events_base_url.rstrip("/"),
    }


class WebUIRequestHandler(SimpleHTTPRequestHandler):
    runtime_config: Dict[str, str] = {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/config":
            payload = json.dumps(self.runtime_config, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def run_server(
    host: str = "127.0.0.1",
    port: int = 8110,
    core_base_url: str = "http://127.0.0.1:8080/api/v1",
    video_base_url: str = "http://127.0.0.1:8090/api/v1",
    events_base_url: str = "http://127.0.0.1:8100/api/v1",
) -> None:
    runtime_config = build_runtime_config(core_base_url, video_base_url, events_base_url)
    class ConfiguredHandler(WebUIRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    ConfiguredHandler.runtime_config = runtime_config
    server = ThreadingHTTPServer((host, port), ConfiguredHandler)
    print(f"Web UI listening on http://{host}:{port}")
    server.serve_forever()
