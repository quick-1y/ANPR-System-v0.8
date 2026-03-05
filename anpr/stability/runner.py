from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass
class ProbeResult:
    ok: bool
    latency_ms: float
    status_code: int


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return min(values)
    if q >= 1:
        return max(values)
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


class StabilitySuite:
    def __init__(self, core_url: str, video_url: str, events_url: str, timeout_s: float = 2.0) -> None:
        self.core_url = core_url.rstrip("/")
        self.video_url = video_url.rstrip("/")
        self.events_url = events_url.rstrip("/")
        self.timeout_s = timeout_s

    def run(self, requests_count: int = 20) -> Dict[str, object]:
        health = self._health_checks()
        load = self._load_probe(requests_count=requests_count)
        degradation = self._degradation_probe()
        summary_status = "ok" if health["ok"] and load["error_rate"] < 0.1 and degradation["ok"] else "degraded"
        return {
            "status": summary_status,
            "health": health,
            "load": load,
            "degradation": degradation,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def _health_checks(self) -> Dict[str, object]:
        endpoints = {
            "core": f"{self.core_url}/health",
            "video": f"{self.video_url}/video/health",
            "events": f"{self.events_url}/events/health",
        }
        details: Dict[str, object] = {}
        ok = True
        for name, url in endpoints.items():
            result = self._probe("GET", url)
            details[name] = {
                "ok": result.ok,
                "latency_ms": round(result.latency_ms, 2),
                "status_code": result.status_code,
            }
            ok = ok and result.ok
        return {"ok": ok, "details": details}

    def _load_probe(self, requests_count: int = 20) -> Dict[str, object]:
        latencies: List[float] = []
        errors = 0
        for idx in range(requests_count):
            payload = {
                "channel_id": "stability-gate",
                "plate": f"T{idx:03d}AA77",
                "confidence": 0.8,
            }
            result = self._probe("POST", f"{self.events_url}/events/publish", payload)
            latencies.append(result.latency_ms)
            if not result.ok:
                errors += 1

        error_rate = errors / requests_count if requests_count > 0 else 0
        return {
            "requests": requests_count,
            "errors": errors,
            "error_rate": round(error_rate, 4),
            "latency_ms": {
                "avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
                "p50": round(percentile(latencies, 0.5), 2),
                "p95": round(percentile(latencies, 0.95), 2),
                "max": round(max(latencies), 2) if latencies else 0.0,
            },
        }

    def _degradation_probe(self) -> Dict[str, object]:
        self._probe(
            "POST",
            f"{self.events_url}/events/telemetry",
            {
                "channel_id": "stability-gate",
                "reconnects": 5,
                "timeouts": 4,
                "latency_ms": 800,
            },
        )
        alerts = self._request_json("GET", f"{self.events_url}/events/alerts")
        items = alerts.get("items", []) if isinstance(alerts, dict) else []
        has_required = any(item.get("kind") == "reconnect_warn" for item in items) and any(
            item.get("kind") == "timeout_warn" for item in items
        )
        return {"ok": bool(has_required), "alerts_total": len(items)}

    def _request_json(self, method: str, url: str, payload: Dict[str, object] | None = None) -> Dict[str, object]:
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            body = response.read() or b"{}"
            return json.loads(body.decode("utf-8"))

    def _probe(self, method: str, url: str, payload: Dict[str, object] | None = None) -> ProbeResult:
        started = time.perf_counter()
        try:
            data = None
            headers = {"Content-Type": "application/json"}
            if payload is not None:
                data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                status = int(response.getcode() or 0)
            latency_ms = (time.perf_counter() - started) * 1000
            return ProbeResult(ok=200 <= status < 300, latency_ms=latency_ms, status_code=status)
        except urllib.error.HTTPError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return ProbeResult(ok=False, latency_ms=latency_ms, status_code=int(exc.code))
        except Exception:
            latency_ms = (time.perf_counter() - started) * 1000
            return ProbeResult(ok=False, latency_ms=latency_ms, status_code=0)


def main() -> None:
    parser = argparse.ArgumentParser(description="ANPR stage-6 stability suite")
    parser.add_argument("--core-url", default="http://127.0.0.1:8080/api/v1")
    parser.add_argument("--video-url", default="http://127.0.0.1:8090/api/v1")
    parser.add_argument("--events-url", default="http://127.0.0.1:8100/api/v1")
    parser.add_argument("--requests", default=20, type=int)
    args = parser.parse_args()

    suite = StabilitySuite(core_url=args.core_url, video_url=args.video_url, events_url=args.events_url)
    report = suite.run(requests_count=max(1, args.requests))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
