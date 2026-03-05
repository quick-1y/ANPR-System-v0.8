# Этап 1 — Базовый каркас ANPR Core Service

На этом этапе заложен первый рабочий headless-слой `ANPR Core Service`, который не зависит от desktop UI.

## Что реализовано

1. Создан пакет `anpr/core/` с in-memory сервисом управления каналами.
2. Добавлен HTTP API (stdlib `http.server`) с endpoint-ами v1:
   - `GET /api/v1/health`
   - `GET /api/v1/metrics`
   - `GET /api/v1/channels`
   - `POST /api/v1/channels`
   - `GET /api/v1/channels/{id}`
   - `PATCH /api/v1/channels/{id}`
   - `POST /api/v1/channels/{id}/start|stop|restart`
   - `PUT /api/v1/channels/{id}/roi`
   - `PUT /api/v1/channels/{id}/filters`
   - `PUT /api/v1/channels/{id}/lists`
3. Подготовлены unit-тесты для сценариев управления каналами и метрик очередей.

## Как запустить

```bash
python -m anpr.core --host 127.0.0.1 --port 8080
```

## Ограничения текущего шага

- Хранилище состояния каналов пока in-memory (без персистентности).
- Пайплайн детекции/OCR пока не подключён к HTTP API.
- Event stream (WebSocket/SSE) и Video Gateway реализуются в следующих этапах.

## Следующая итерация

- Подключить `ChannelWorker`/pipeline к жизненному циклу каналов через сервисный слой.
- Перенести хранение каналов и конфигов в персистентный слой.
- Добавить контракт событий распознавания для Event & Telemetry Service.
