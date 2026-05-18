from app.api.schemas.common import APIModel


class WidgetConfigResponse(APIModel):
    id: str
    display_name: str
    theme: str
    accent_color: str
