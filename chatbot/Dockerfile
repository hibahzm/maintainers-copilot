FROM python:3.12-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY chatbot/pyproject.toml ./pyproject.toml
RUN uv sync --no-dev --no-install-project

COPY chatbot/app.py ./app.py
COPY chatbot/pages ./pages

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
