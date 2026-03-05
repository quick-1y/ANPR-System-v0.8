# Этап 6 — Stabilization / Production Readiness

На этапе 6 добавлен инструмент стабильности для pre-production проверок и базовый runbook эксплуатации.

## Что реализовано

1. Новый пакет `anpr/stability/`:
   - `runner.py` — Stability Suite для smoke/load/degradation проверок.
   - `__main__.py` — CLI-запуск набора проверок.

2. Реализованные проверки:
   - **Health probe** сервисов `core`, `video_gateway`, `event_telemetry`.
   - **Load probe** публикации событий и расчёт `avg/p50/p95/max` latency + `error_rate`.
   - **Degradation probe**: имитация reconnect/timeout/latency деградации и проверка алертов.

3. Отчёт:
   - JSON-вывод с секциями `health`, `load`, `degradation` и итоговым `status`.

## Как запускать

```bash
python3 -m anpr.stability \
  --core-url http://127.0.0.1:8080/api/v1 \
  --video-url http://127.0.0.1:8090/api/v1 \
  --events-url http://127.0.0.1:8100/api/v1 \
  --requests 50
```

## Мини-runbook

1. Если `health.ok = false`:
   - проверить доступность endpoint-ов `health` каждого сервиса;
   - проверить логи запуска и порты bind (`0.0.0.0`/`127.0.0.1`).
2. Если `load.error_rate >= 0.1`:
   - снизить нагрузку по каналам/частоте polling;
   - проверить timeouts и сетевые лимиты.
3. Если `degradation.ok = false`:
   - проверить генерацию телеметрии с каналов;
   - проверить пороги алертов в Event & Telemetry Service.

## Следующий шаг

- Вынести Stability Suite в CI-пайплайн как обязательный gate перед релизом.
- Добавить длительный soak-test (30–60 минут) и персистентные отчёты по трендам latency/error-rate.
