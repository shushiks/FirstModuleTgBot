FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml uv.lock Readme.md ./
RUN pip install uv==0.11.29 && uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts

RUN mkdir -p /data/media /data/logs && chown -R app:app /app /data/media /data/logs
USER app

CMD ["uvicorn", "zero_semester.admin.main:app", "--host", "0.0.0.0", "--port", "8000"]
