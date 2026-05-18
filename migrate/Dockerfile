FROM python:3.12-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY migrate/pyproject.toml ./pyproject.toml
RUN uv sync --no-dev --no-install-project

COPY migrate/entrypoint.sh ./entrypoint.sh
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
