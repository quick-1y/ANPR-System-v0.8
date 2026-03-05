# Этап 4 — Web UI (MVP)

На этапе 4 добавлен минимально рабочий web-интерфейс оператора с тремя ключевыми блоками:

1. **Dashboard каналов** (данные из ANPR Core + Video Gateway).
2. **Карточки событий ANPR** в реальном времени (polling из Event & Telemetry Service).
3. **Конфигуратор канала** (создание канала и связанного видеопотока).

## Что реализовано

- Новый пакет `anpr/web_ui/`:
  - `server.py` — сервис раздачи статического UI и runtime-конфига endpoint-ов.
  - `__main__.py` — CLI-запуск Web UI сервиса.
  - `static/index.html` — dashboard, события, конфигуратор.
  - `static/app.js` — интеграция с API Core/Video/Event.
  - `static/styles.css` — базовая тёмная тема интерфейса.

- Endpoint Web UI сервиса:
  - `GET /api/config` — runtime-конфиг базовых URL backend-сервисов.

## Как запустить

```bash
python -m anpr.web_ui --host 127.0.0.1 --port 8110 \
  --core-base-url http://127.0.0.1:8080/api/v1 \
  --video-base-url http://127.0.0.1:8090/api/v1 \
  --events-base-url http://127.0.0.1:8100/api/v1
```

## Ограничения текущего MVP

- Используется polling событий, без WebSocket/SSE.
- Нет ролей/аутентификации.
- Нет продвинутой работы с ROI-полигоном (только базовый флаг в форме).

## Следующий шаг

- Подключить Event stream через WebSocket/SSE.
- Добавить расширенный конфигуратор ROI/фильтров/списков.
- Подготовить UI для адаптивной видеосетки с переключением профилей качества.
