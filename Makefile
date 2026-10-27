.PHONY: install run down migrate migration test lint format

install:
	python -m pip install -e '.[dev]'

run:
	docker compose up --build

down:
	docker compose down

migrate:
	docker compose run --rm admin alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(name)"

test:
	pytest

lint:
	ruff check .
	mypy src

format:
	ruff format .
	ruff check --fix .
