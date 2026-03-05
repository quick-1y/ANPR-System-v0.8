from __future__ import annotations

import argparse

from .http_api import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Video Gateway Service API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8090, type=int)
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
