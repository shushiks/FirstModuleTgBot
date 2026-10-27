# Деплой

Для первого релиза используется Docker Compose:

- `postgres` — PostgreSQL;
- `admin` — FastAPI;
- `bot` — aiogram polling;
- `worker` — рассылки и фоновые задания.

Перед обновлением приложения выполняется `alembic upgrade head`. PostgreSQL и `/data/media` подключены как постоянные Docker volumes.
