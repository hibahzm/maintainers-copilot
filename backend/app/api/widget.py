from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.api.dependencies import AdminUserDep, SettingsDep, WidgetServiceDep
from app.api.schemas.widget import (
    PublicWidgetConfigResponse,
    WidgetConfigResponse,
    WidgetConfigUpsertRequest,
)
from app.infra.exceptions import NotFoundError, PermissionDenied

router = APIRouter(prefix="/widget", tags=["widget"])


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


@router.get("/widget.js")
async def widget_loader(service: WidgetServiceDep, settings: SettingsDep) -> Response:
    return Response(
        content=service.loader_script(widget_public_url=settings.widget_public_url),
        media_type="application/javascript",
    )
