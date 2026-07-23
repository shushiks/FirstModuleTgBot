# Нулевой семестр

Telegram-бот курса «Нулевой семестр» и FastAPI-админка для управления контентом.

## Быстрый запуск

1. Скопировать `.env.example` в `.env` и заполнить секреты.
2. Запустить БД: `docker compose up -d postgres`.
3. Применить миграции: `docker compose run --rm admin alembic upgrade head`.
4. Создать администратора: `docker compose run --rm admin python scripts/create_admin.py admin`.
5. Запустить приложение: `docker compose up --build admin bot worker`.

Админка доступна на `http://localhost:8000`. Бот по умолчанию работает через polling.

Подробности: [архитектура](docs/ARCHITECTURE.md) и [схема БД](docs/DATABASE.md).

## Локальные проверки

```bash
uv sync --extra dev
uv run ruff check .
uv run mypy src
uv run pytest
```
