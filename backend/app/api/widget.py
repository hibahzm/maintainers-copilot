from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    AdminUserDep,
    ChatServiceDep,
    OptionalCurrentUserDep,
    SettingsDep,
    WidgetServiceDep,
)
from app.api.schemas.chat import ChatRequest
from app.api.schemas.widget import (
    PublicWidgetConfigResponse,
    WidgetConfigResponse,
    WidgetConfigUpsertRequest,
)
from app.api.streaming import chat_sse_events
from app.infra.exceptions import NotFoundError, PermissionDenied

router = APIRouter(prefix="/widget", tags=["widget"])
loader_router = APIRouter(tags=["widget"])


@router.get("/config/{widget_id}", response_model=PublicWidgetConfigResponse)
async def get_widget_config(
    widget_id: str,
    request: Request,
    service: WidgetServiceDep,
) -> PublicWidgetConfigResponse:
    request_origin = (
        request.headers.get("x-widget-origin")
        or request.headers.get("origin")
        or service.origin_from_referer(request.headers.get("referer"))
    )
    try:
        return await service.get_public_config(widget_id, request_origin=request_origin)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/admin/configs", response_model=list[WidgetConfigResponse])
async def list_widget_configs(
    admin_user: AdminUserDep,
    service: WidgetServiceDep,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[WidgetConfigResponse]:
    _ = admin_user
    return await service.list_configs(limit=limit)


@router.put("/admin/config/{widget_id}", response_model=WidgetConfigResponse)
async def upsert_widget_config(
    widget_id: str,
    payload: WidgetConfigUpsertRequest,
    admin_user: AdminUserDep,
    service: WidgetServiceDep,
) -> WidgetConfigResponse:
    if payload.widget_id != widget_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path widget_id must match payload widget_id.",
        )
    return await service.upsert_config(payload=payload, actor_user_id=admin_user.id)


@router.post("/{widget_id}/chat/stream")
async def stream_widget_chat_response(
    widget_id: str,
    payload: ChatRequest,
    request: Request,
    widget_service: WidgetServiceDep,
    chat_service: ChatServiceDep,
    current_user: OptionalCurrentUserDep,
) -> StreamingResponse:
    request_origin = (
        request.headers.get("x-widget-origin")
        or request.headers.get("origin")
        or widget_service.origin_from_referer(request.headers.get("referer"))
    )
    try:
        config = await widget_service.get_public_config(widget_id, request_origin=request_origin)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    chat_payload = payload.model_copy(
        update=_chat_policy_from_widget_tools(config.enabled_tools),
    )
    return StreamingResponse(
        chat_sse_events(
            payload=chat_payload,
            service=chat_service,
            user_id=current_user.id if current_user else None,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/widget.js")
async def widget_loader(service: WidgetServiceDep, settings: SettingsDep) -> Response:
    return _widget_loader_response(service=service, settings=settings)


@loader_router.get("/widget.js")
async def root_widget_loader(service: WidgetServiceDep, settings: SettingsDep) -> Response:
    return _widget_loader_response(service=service, settings=settings)


@router.get("/frame/{widget_id}")
async def widget_frame(
    widget_id: str,
    request: Request,
    service: WidgetServiceDep,
    settings: SettingsDep,
    widget_url: str | None = Query(default=None, alias="widgetUrl"),
    api_base: str | None = Query(default=None, alias="apiBase"),
    host_origin: str | None = Query(default=None, alias="hostOrigin"),
) -> Response:
    request_origin = (
        host_origin
        or request.headers.get("origin")
        or service.origin_from_referer(request.headers.get("referer"))
    )
    try:
        html, frame_ancestors = await service.get_frame_html(
            widget_id,
            request_origin=request_origin,
            widget_public_url=widget_url or settings.widget_public_url,
            api_base=api_base or str(request.base_url).rstrip("/"),
            host_origin=host_origin,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Content-Security-Policy": (
                "default-src 'self'; "
                f"frame-src {widget_url or settings.widget_public_url}; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "object-src 'none'; base-uri 'none'; "
                f"{frame_ancestors};"
            )
        },
    )


def _widget_loader_response(*, service: WidgetServiceDep, settings: SettingsDep) -> Response:
    return Response(
        content=service.loader_script(widget_public_url=settings.widget_public_url),
        media_type="application/javascript",
    )


def _chat_policy_from_widget_tools(enabled_tools: list[str]) -> dict:
    mapped_tools = ["auto"]
    if "rag_search" in enabled_tools:
        mapped_tools.append("rag")
    if "classify_issue" in enabled_tools:
        mapped_tools.append("classifier")
    if "extract_entities" in enabled_tools:
        mapped_tools.append("ner")
    if "summarize_issue" in enabled_tools:
        mapped_tools.append("summarizer")

    if len(mapped_tools) == 1:
        mapped_tools = []

    return {
        "tools": mapped_tools,
        "use_rag": "rag_search" in enabled_tools,
        "allow_summarizer": "summarize_issue" in enabled_tools,
        "allow_memory_write": False,
    }
