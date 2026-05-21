from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, chat, classifier, memory, rag, widget
from app.core.config import settings
from app.infra.exceptions import DomainError, NotFoundError, PermissionDenied, ToolFailure
from app.infra.startup_checks import (
    assert_eval_thresholds_enabled,
    assert_runtime_secrets_non_empty,
    assert_tracing_configured,
)
from app.infra.tracing import RequestTracingMiddleware, trace_event
from app.infra.vault import VaultClient
from app.services.bootstrap import bootstrap_dev_data
from app.services.rag_bootstrap import bootstrap_rag_index


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
        await bootstrap_dev_data(settings)
        await bootstrap_rag_index(settings)
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
app.include_router(widget.loader_router)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = _domain_status_code(exc)
    request_id = getattr(request.state, "request_id", None)
    trace_event(
        "api.domain_error",
        error_type=type(exc).__name__,
        status_code=status_code,
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": _domain_error_code(exc),
                "message": str(exc),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def uncaught_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    trace_event(
        "api.uncaught_error",
        error_type=type(exc).__name__,
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "Unexpected server error.",
                "request_id": request_id,
            }
        },
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _configure_langfuse_environment(runtime_secrets) -> None:
    os.environ["LANGFUSE_PUBLIC_KEY"] = runtime_secrets.langfuse_public_key.get_secret_value()
    os.environ["LANGFUSE_SECRET_KEY"] = runtime_secrets.langfuse_secret_key.get_secret_value()
    os.environ["LANGFUSE_BASE_URL"] = settings.tracing_host


def _domain_status_code(exc: DomainError) -> int:
    if isinstance(exc, NotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(exc, PermissionDenied):
        return status.HTTP_403_FORBIDDEN
    if isinstance(exc, ToolFailure):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_400_BAD_REQUEST


def _domain_error_code(exc: DomainError) -> str:
    if isinstance(exc, NotFoundError):
        return "not_found"
    if isinstance(exc, PermissionDenied):
        return "permission_denied"
    if isinstance(exc, ToolFailure):
        return "tool_failure"
    return "domain_error"
