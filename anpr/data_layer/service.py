from __future__ import annotations

import csv
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional


class DataLayerService:
    """Data Layer: retention/rotation/export событий и медиа-артефактов."""

    def __init__(self, db_path: str = "data/db/anpr.db", media_root: str = "data/screenshots") -> None:
        self.db_path = db_path
        self.media_root = media_root
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.media_root).mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    plate TEXT NOT NULL,
                    country TEXT,
                    confidence REAL,
                    source TEXT,
                    frame_path TEXT,
                    plate_path TEXT,
                    direction TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)")
            conn.commit()

    def insert_demo_event(self, channel: str, plate: str, timestamp: Optional[str] = None) -> int:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO events (timestamp, channel, plate, confidence, source) VALUES (?, ?, ?, ?, ?)",
                (ts, channel, plate, 0.9, "demo"),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def retention_delete_older_than_days(self, days: int) -> Dict[str, int | str]:
        if days < 0:
            raise ValueError("days должен быть >= 0")
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff_iso,))
            conn.commit()
            return {
                "deleted_events": int(cursor.rowcount if cursor.rowcount is not None else 0),
                "cutoff_utc": cutoff_iso,
            }

    def export_events_json(self, output_path: str, limit: int = 1000) -> Dict[str, object]:
        if limit <= 0:
            raise ValueError("limit должен быть > 0")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY datetime(timestamp) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        payload = [dict(row) for row in rows]
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"path": str(output), "exported": len(payload), "format": "json"}

    def export_events_csv(self, output_path: str, limit: int = 1000) -> Dict[str, object]:
        if limit <= 0:
            raise ValueError("limit должен быть > 0")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY datetime(timestamp) DESC LIMIT ?",
                (limit,),
            ).fetchall()

        headers: List[str] = [
            "id",
            "timestamp",
            "channel",
            "plate",
            "country",
            "confidence",
            "source",
            "frame_path",
            "plate_path",
            "direction",
        ]
        with output.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        return {"path": str(output), "exported": len(rows), "format": "csv"}

    def media_rotation_cleanup(self) -> Dict[str, int]:
        removed_files = 0
        for root, _, files in os.walk(self.media_root):
            for filename in files:
                path = Path(root) / filename
                if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                    continue
                if path.stat().st_size == 0:
                    path.unlink(missing_ok=True)
                    removed_files += 1
        return {"removed_files": removed_files}

    def health(self) -> Dict[str, object]:
        with self._connect() as conn:
            events_total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {
            "status": "ok",
            "db_path": self.db_path,
            "media_root": self.media_root,
            "events_total": int(events_total),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
