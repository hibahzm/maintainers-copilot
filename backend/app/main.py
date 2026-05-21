from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, classifier, memory, rag, widget
from app.core.config import settings
from app.infra.startup_checks import (
    assert_eval_thresholds_enabled,
    assert_runtime_secrets_non_empty,
    assert_tracing_configured,
)
from app.infra.tracing import RequestTracingMiddleware
from app.infra.vault import VaultClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    vault = VaultClient(settings)
    try:
        await vault.assert_reachable()
        app.state.runtime_secrets = await vault.load_runtime_secrets()
        assert_runtime_secrets_non_empty(app.state.runtime_secrets)
        assert_tracing_configured(settings, app.state.runtime_secrets)
        _configure_langfuse_environment(app.state.runtime_secrets)
        assert_eval_thresholds_enabled(Path(settings.eval_thresholds_path))
        yield
    finally:
        await vault.aclose()


app = FastAPI(title="Maintainers Copilot API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTracingMiddleware)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(classifier.router)
app.include_router(rag.router)
app.include_router(memory.router)
app.include_router(widget.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _configure_langfuse_environment(runtime_secrets) -> None:
    os.environ["LANGFUSE_PUBLIC_KEY"] = runtime_secrets.langfuse_public_key.get_secret_value()
    os.environ["LANGFUSE_SECRET_KEY"] = runtime_secrets.langfuse_secret_key.get_secret_value()
    os.environ["LANGFUSE_BASE_URL"] = settings.tracing_host
