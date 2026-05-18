FROM python:3.12-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY model_server/pyproject.toml ./pyproject.toml
RUN uv sync --no-dev --no-install-project

COPY model_server ./model_server

EXPOSE 8001

CMD ["uvicorn", "model_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
