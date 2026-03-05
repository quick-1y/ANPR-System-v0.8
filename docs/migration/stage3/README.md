# Этап 3 — Event & Telemetry Service

На этом этапе добавлен отдельный headless `Event & Telemetry Service` для доставки событий распознавания в web UI и публикации телеметрии каналов.

## Что реализовано

1. Новый пакет `anpr/event_telemetry/`:
   - `models.py` — модели события распознавания (`ANPREvent`) и телеметрии канала (`ChannelTelemetry`).
   - `service.py` — in-memory сервис подписки/поллинга событий, приёма телеметрии и генерации алертов.
   - `http_api.py` — API для публикации/получения событий, метрик, health-check и алертов.
   - `__main__.py` — CLI-запуск сервиса.

2. Реализованы endpoint-ы:
   - `GET /api/v1/events/health`
   - `GET /api/v1/events/metrics`
   - `GET /api/v1/events/telemetry`
   - `GET /api/v1/events/alerts`
   - `GET /api/v1/events/poll?subscriber_id=...&limit=...`
   - `POST /api/v1/events/subscribe`
   - `POST /api/v1/events/publish`
   - `POST /api/v1/events/telemetry`

3. Реализована базовая логика алертов:
   - `reconnect_warn` при `reconnects >= 3`
   - `timeout_warn` при `timeouts >= 3`
   - `latency_warn` при `latency_ms >= 500`

## Как запустить

```bash
python -m anpr.event_telemetry --host 127.0.0.1 --port 8100
```

## Ограничения текущей реализации

- Для потока событий используется polling-модель (подписка + cursor), без WebSocket/SSE transport.
- События и телеметрия пока хранятся in-memory.

## Следующий шаг

- Добавить WebSocket/SSE транспорт поверх текущего event-слоя.
- Подключить `ANPR Core Service` и `Video Gateway` к единому событийному контуру.
