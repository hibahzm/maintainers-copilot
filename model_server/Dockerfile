FROM python:3.12-slim-trixie

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    UV_HTTP_TIMEOUT=120 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    RAG_EMBEDDING_MODEL=/app/models/e5-small-v2 \
    TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --progress-bar off --timeout 300 --retries 10 uv==0.11.11

COPY model_server/pyproject.toml ./pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

COPY model_server ./model_server

EXPOSE 8001

CMD ["uvicorn", "model_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
