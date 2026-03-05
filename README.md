# ANPR System v0.8 Web

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)
![Web UI](https://img.shields.io/badge/UI-Web-2563eb.svg)
![YOLOv8](https://img.shields.io/badge/Detection-YOLOv8-red.svg)
![CRNN](https://img.shields.io/badge/OCR-CRNN-orange.svg)

Проект полностью переведён с desktop-архитектуры на web-архитектуру.

## Новая архитектура

### 1) ANPR Core Service (backend)
- Сохранён действующий пайплайн `detector -> OCR -> postprocessing`.
- Для каждого канала запускается независимый runtime-поток обработки.
- REST API для управления каналами и ROI.

### 2) Video Gateway
- Приём источников RTSP/локальных камер через OpenCV.
- В web UI отдаётся оперативный просмотр (snapshot polling).
- В API добавлена точка конфигурации профилей `high/medium/low` и рекомендации по транспорту: WebRTC/HLS/RTSP.

### 3) Event & Telemetry Service
- Real-time события ANPR доставляются в UI через SSE (`/api/events/stream`).
- Метрики канала: статус, время последнего кадра, reconnect-счётчик.
- Health endpoint: `/api/health`.

### 4) Web UI
- Панель мониторинга каналов (карточки, live snapshot, удаление канала).
- Лента событий распознавания в реальном времени.
- Форма управления каналами.

### 5) Data Layer
- Слой хранения событий из legacy части проекта сохранён в `anpr/infrastructure` и может быть подключён в backend-сервис.
- Рекомендовано выделить отдельное архивное хранилище медиа для production.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

По умолчанию web-приложение доступно на `http://localhost:8080`.

## REST API

- `GET /api/health`
- `GET /api/channels`
- `POST /api/channels`
- `DELETE /api/channels/{channel_id}`
- `PATCH /api/channels/{channel_id}/roi`
- `GET /api/channels/{channel_id}/snapshot`
- `GET /api/telemetry`
- `GET /api/events/stream` (SSE)
- `GET /api/video-gateway/profiles`

## Практические правила веб-режима

- Не отправлять в браузер сырой high-quality поток на все плитки одновременно.
- Использовать профили качества `high/medium/low`.
- Для фоновых плиток снижать FPS/разрешение.
- Декодирование и инференс держать на сервере.

## Структура проекта

```text
ANPR-System-v0.8/
├── app.py
├── requirements.txt
├── README.md
├── anpr/
│   ├── config.py
│   ├── detection/
│   ├── infrastructure/
│   ├── pipeline/
│   ├── postprocessing/
│   ├── preprocessing/
│   ├── recognition/
│   ├── services/
│   │   └── channel_service.py
│   └── web/
│       ├── main.py
│       └── routes.py
├── webui/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── config/
├── models/
└── settings.json
```
