# Этап 5 — Data Layer (retention / rotation / export)

На этапе 5 выделен отдельный headless `Data Layer Service` для управления жизненным циклом данных событий и медиа-артефактов.

## Что реализовано

1. Новый пакет `anpr/data_layer/`:
   - `service.py` — сервис хранения/обслуживания данных.
   - `http_api.py` — API операций retention/rotation/export.
   - `__main__.py` — CLI-запуск сервиса.

2. Реализованы базовые операции Data Layer:
   - retention событий: удаление записей старше N дней;
   - экспорт событий в JSON и CSV;
   - cleanup медиа (удаление пустых изображений);
   - health endpoint с метрикой количества событий.

3. Реализованы endpoint-ы:
   - `GET /api/v1/data/health`
   - `POST /api/v1/data/retention`
   - `POST /api/v1/data/export/json`
   - `POST /api/v1/data/export/csv`
   - `POST /api/v1/data/media/cleanup`

## Как запустить

```bash
python3 -m anpr.data_layer --host 127.0.0.1 --port 8120
```

## Ограничения текущей реализации

- Политики ротации пока базовые (без фонового scheduler).
- Нет object storage backend, работа идёт с локальной файловой системой.

## Следующий шаг

- Добавить планировщик фоновых задач retention/rotation.
- Добавить экспорт через API потоковой выгрузкой (streaming) и архивирование.
