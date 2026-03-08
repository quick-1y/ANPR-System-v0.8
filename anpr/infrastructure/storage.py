from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from .logging_manager import get_logger

logger = get_logger(__name__)
_SCHEMA_SQL_PATH = Path(__file__).resolve().parents[2] / "database" / "postgres" / "schema.sql"


class StorageUnavailableError(RuntimeError):
    """БД PostgreSQL временно недоступна."""


class PostgresEventDatabase:
    """PostgreSQL-only хранилище событий с ленивым bootstrap схемы."""

    def __init__(self, dsn: str) -> None:
        self.dsn = str(dsn or "").strip()
        if not self.dsn:
            raise ValueError("postgres_dsn обязателен")
        self._init_lock = threading.Lock()
        self._initialized = False

    @staticmethod
    def _to_dict(row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "timestamp": row[1],
            "channel": row[2],
            "plate": row[3],
            "country": row[4],
            "confidence": row[5],
            "source": row[6],
            "frame_path": row[7],
            "plate_path": row[8],
            "direction": row[9],
        }

    def _connect(self):
        import psycopg  # type: ignore

        return psycopg.connect(self.dsn)

    def _ensure_schema(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            try:
                query = _SCHEMA_SQL_PATH.read_text(encoding="utf-8")
            except OSError as exc:
                raise StorageUnavailableError(f"Не удалось прочитать SQL-схему {_SCHEMA_SQL_PATH}: {exc}") from exc
            try:
                with self._connect() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query)
                    conn.commit()
            except Exception as exc:  # noqa: BLE001
                raise StorageUnavailableError(f"PostgreSQL недоступен: {exc}") from exc
            self._initialized = True

    def insert_event(
        self,
        channel: str,
        plate: str,
        country: Optional[str] = None,
        confidence: float = 0.0,
        source: str = "",
        timestamp: Optional[str] = None,
        frame_path: Optional[str] = None,
        plate_path: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> int:
        self._ensure_schema()
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        (
                            "INSERT INTO events (timestamp, channel, plate, country, confidence, source, frame_path, plate_path, direction) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
                        ),
                        (ts, channel, plate, country, confidence, source, frame_path, plate_path, direction),
                    )
                    row = cursor.fetchone()
                conn.commit()
            return int(row[0]) if row else 0
        except StorageUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise StorageUnavailableError(f"PostgreSQL недоступен: {exc}") from exc

    def fetch_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        self._ensure_schema()
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, timestamp, channel, plate, country, confidence, source, frame_path, plate_path, direction "
                        "FROM events ORDER BY timestamp DESC LIMIT %s",
                        (limit,),
                    )
                    return [self._to_dict(row) for row in cursor.fetchall()]
        except Exception as exc:  # noqa: BLE001
            raise StorageUnavailableError(f"PostgreSQL недоступен: {exc}") from exc

    def fetch_by_id(self, event_id: int) -> Optional[dict[str, Any]]:
        self._ensure_schema()
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, timestamp, channel, plate, country, confidence, source, frame_path, plate_path, direction FROM events WHERE id = %s",
                        (int(event_id),),
                    )
                    row = cursor.fetchone()
                    return self._to_dict(row) if row else None
        except Exception as exc:  # noqa: BLE001
            raise StorageUnavailableError(f"PostgreSQL недоступен: {exc}") from exc

    def delete_before(self, cutoff_iso: str) -> list[dict[str, Any]]:
        self._ensure_schema()
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM events WHERE timestamp < %s RETURNING id, frame_path, plate_path",
                        (cutoff_iso,),
                    )
                    rows = cursor.fetchall()
                conn.commit()
            return [{"id": row[0], "frame_path": row[1], "plate_path": row[2]} for row in rows]
        except Exception as exc:  # noqa: BLE001
            raise StorageUnavailableError(f"PostgreSQL недоступен: {exc}") from exc

    def fetch_for_export(self, *, start: Optional[str] = None, end: Optional[str] = None, channel: Optional[str] = None) -> list[dict[str, Any]]:
        self._ensure_schema()
        filters: list[str] = []
        params: list[Any] = []
        if start:
            filters.append("timestamp >= %s")
            params.append(start)
        if end:
            filters.append("timestamp <= %s")
            params.append(end)
        if channel:
            filters.append("channel = %s")
            params.append(channel)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        query = (
            "SELECT id, timestamp, channel, plate, country, confidence, source, frame_path, plate_path, direction "
            f"FROM events {where} ORDER BY timestamp DESC"
        )
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, tuple(params))
                    return [self._to_dict(row) for row in cursor.fetchall()]
        except Exception as exc:  # noqa: BLE001
            raise StorageUnavailableError(f"PostgreSQL недоступен: {exc}") from exc


class AsyncEventDatabase:
    """Асинхронный адаптер над PostgreSQL-only storage."""

    def __init__(self, dsn: str) -> None:
        self._sync_db = PostgresEventDatabase(dsn)

    async def insert_event_async(
        self,
        channel: str,
        plate: str,
        confidence: float = 0.0,
        source: str = "",
        timestamp: Optional[str] = None,
        frame_path: Optional[str] = None,
        plate_path: Optional[str] = None,
        country: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> int:
        return await asyncio.to_thread(
            self._sync_db.insert_event,
            channel,
            plate,
            country,
            confidence,
            source,
            timestamp,
            frame_path,
            plate_path,
            direction,
        )


__all__ = ["PostgresEventDatabase", "AsyncEventDatabase", "StorageUnavailableError"]
