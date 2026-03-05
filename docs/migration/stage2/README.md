# Этап 2 — Video Gateway (control-plane)

На этом этапе добавлен базовый `Video Gateway Service` как отдельный headless-компонент, который управляет видеопотоками и профилями качества для web-клиентов.

## Что реализовано

1. Новый пакет `anpr/video_gateway/`:
   - `models.py` — модели потоков, сессий и профилей качества.
   - `service.py` — сервис управления RTSP-источниками, профилями (`high/medium/low`) и созданием сессий `WebRTC/HLS`.
   - `http_api.py` — API управления потоками и сессиями.
   - `__main__.py` — CLI-запуск сервиса.

2. Реализованы endpoint-ы:
   - `GET /api/v1/video/health`
   - `GET /api/v1/video/metrics`
   - `GET /api/v1/video/profiles`
   - `GET /api/v1/video/streams`
   - `GET /api/v1/video/streams/{stream_id}`
   - `POST /api/v1/video/streams`
   - `POST /api/v1/video/streams/{stream_id}/enable`
   - `POST /api/v1/video/streams/{stream_id}/profile`
   - `POST /api/v1/video/streams/{stream_id}/tile-activity`
   - `POST /api/v1/video/streams/{stream_id}/session`

3. Добавлена автоматическая политика выбора профиля под активность плитки:
   - `focused -> high`
   - `visible -> medium`
   - `background -> low`

## Как запустить

```bash
python -m anpr.video_gateway --host 127.0.0.1 --port 8090
```

## Ограничения текущей реализации

- Реализован control-plane и API-контракт; полноценный media-plane (реальная перекодировка/relay) будет добавлен в следующих итерациях.
- Состояние потоков и сессий пока хранится in-memory.

## Следующий шаг

- Подключить реальный media backend (RTSP ingest + транскодирование профилей).
- Добавить интеграцию с Event & Telemetry Service для алертов по reconnect/timeouts и QoS-метрик видеодоставки.
