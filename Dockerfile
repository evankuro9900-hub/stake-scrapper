FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.3 \
    && poetry config virtualenvs.in-project true

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --no-interaction --no-ansi

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv .venv/
COPY app ./app
COPY frontend_dist ./frontend_dist

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
