from fastapi import APIRouter

from app.api.dependencies import WidgetServiceDep
from app.api.schemas.common import FeatureStubResponse
from app.api.schemas.widget import WidgetConfigResponse

router = APIRouter(prefix="/widget", tags=["widget"])


@router.get("/config/{widget_id}", response_model=WidgetConfigResponse)
async def get_widget_config(
    widget_id: str,
    service: WidgetServiceDep,
) -> WidgetConfigResponse:
    _ = service
    return WidgetConfigResponse(
        id=widget_id,
        display_name="TODO",
        theme="light",
        accent_color="#2563eb",
    )


@router.get("/widget.js", response_model=FeatureStubResponse)
async def widget_loader(service: WidgetServiceDep) -> FeatureStubResponse:
    _ = service
    return FeatureStubResponse(feature="widget loader")
