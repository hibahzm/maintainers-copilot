"""Trace/span helpers for request and tool execution trees."""

from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Identifiers that let logs, spans, and user-facing errors join the same request."""

    request_id: str
    trace_id: str


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Bind stable request/trace identifiers for the lifetime of each HTTP request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        context = TraceContext(
            request_id=request.headers.get(REQUEST_ID_HEADER, _new_id()),
            trace_id=request.headers.get(TRACE_ID_HEADER, _new_id()),
        )
        request.state.request_id = context.request_id
        request.state.trace_id = context.trace_id

        request_token, trace_token = bind_trace_context(context)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = context.request_id
            response.headers[TRACE_ID_HEADER] = context.trace_id
            return response
        finally:
            reset_trace_context(request_token, trace_token)


def bind_trace_context(context: TraceContext) -> tuple[Token[str | None], Token[str | None]]:
    """Store the active identifiers so downstream code can join logs and spans."""
    return _request_id_var.set(context.request_id), _trace_id_var.set(context.trace_id)


def reset_trace_context(
    request_token: Token[str | None],
    trace_token: Token[str | None],
) -> None:
    """Restore the previous context after a request or nested operation finishes."""
    _request_id_var.reset(request_token)
    _trace_id_var.reset(trace_token)


def current_request_id() -> str | None:
    """Return the request ID bound to the current execution context."""
    return _request_id_var.get()


def current_trace_id() -> str | None:
    """Return the trace ID bound to the current execution context."""
    return _trace_id_var.get()


def current_trace_context() -> TraceContext | None:
    """Return the active trace context when one exists."""
    request_id = current_request_id()
    trace_id = current_trace_id()
    if request_id is None or trace_id is None:
        return None
    return TraceContext(request_id=request_id, trace_id=trace_id)


def _new_id() -> str:
    return uuid4().hex
