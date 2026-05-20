"""Widget configuration and embed-snippet workflows."""

from uuid import UUID
from urllib.parse import quote

from app.api.schemas.widget import (
    PublicWidgetConfigResponse,
    WidgetConfigResponse,
    WidgetConfigUpsertRequest,
)
from app.infra.exceptions import NotFoundError, PermissionDenied
from app.repositories.widget_repo import WidgetConfigRecord, WidgetRepository


class WidgetService:
    """Manage public widget config and admin-owned configuration changes."""

    def __init__(self, *, repository: WidgetRepository) -> None:
        self.repository = repository

    async def upsert_config(
        self,
        *,
        payload: WidgetConfigUpsertRequest,
        actor_user_id: UUID,
    ) -> WidgetConfigResponse:
        record = await self.repository.upsert_config(
            widget_id=payload.widget_id,
            allowed_origins=payload.allowed_origins,
            theme=payload.theme,
            greeting=payload.greeting,
            enabled_tools=list(payload.enabled_tools),
            created_by_user_id=actor_user_id,
        )
        return self._response(record)

    async def get_public_config(
        self,
        widget_id: str,
        *,
        request_origin: str | None,
    ) -> PublicWidgetConfigResponse:
        record = await self.repository.get_config(widget_id)
        if record is None:
            raise NotFoundError("Widget config not found.")
        if record.allowed_origins and request_origin not in record.allowed_origins:
            raise PermissionDenied("Origin is not allowed for this widget.")
        return PublicWidgetConfigResponse(
            widget_id=record.widget_id,
            theme=record.theme,
            greeting=record.greeting,
            enabled_tools=record.enabled_tools,
        )

    def origin_from_referer(self, referer: str | None) -> str | None:
        if not referer:
            return None
        try:
            from urllib.parse import urlparse

            parsed = urlparse(referer)
            if not parsed.scheme or not parsed.netloc:
                return None
            return f"{parsed.scheme}://{parsed.netloc}"
        except ValueError:
            return None

    async def list_configs(self, *, limit: int = 100) -> list[WidgetConfigResponse]:
        records = await self.repository.list_configs(limit=limit)
        return [self._response(record) for record in records]

    def loader_script(self, *, widget_public_url: str) -> str:
        widget_url = quote(widget_public_url.rstrip("/"), safe=":/")
        return f"""(() => {{
  const script = document.currentScript;
  const widgetId = script?.dataset.widgetId || "maintainers-copilot";
  const apiBase = script?.dataset.apiBase || new URL(script.src).origin;
  const widgetBase = script?.dataset.widgetUrl || "{widget_url}";
  const hostOrigin = window.location.origin;
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = script?.dataset.label || "Ask Maintainers Copilot";
  button.style.cssText = [
    "position:fixed",
    "right:24px",
    "bottom:24px",
    "z-index:2147483647",
    "border:0",
    "border-radius:999px",
    "padding:12px 16px",
    "background:#2563eb",
    "color:#fff",
    "font:600 14px system-ui,sans-serif",
    "box-shadow:0 10px 30px rgba(15,23,42,.25)",
    "cursor:pointer"
  ].join(";");

  const iframe = document.createElement("iframe");
  iframe.title = "Maintainers Copilot";
  iframe.src = `${{widgetBase}}/?widgetId=${{encodeURIComponent(widgetId)}}&apiBase=${{encodeURIComponent(apiBase)}}&hostOrigin=${{encodeURIComponent(hostOrigin)}}`;
  iframe.style.cssText = [
    "position:fixed",
    "right:24px",
    "bottom:78px",
    "z-index:2147483647",
    "width:380px",
    "height:560px",
    "max-width:calc(100vw - 32px)",
    "border:0",
    "border-radius:18px",
    "box-shadow:0 20px 60px rgba(15,23,42,.28)",
    "display:none",
    "background:#fff"
  ].join(";");

  button.addEventListener("click", () => {{
    iframe.style.display = iframe.style.display === "none" ? "block" : "none";
  }});

  window.addEventListener("message", (event) => {{
    if (event.data?.type !== "widget:resize") return;
    const height = Number(event.data.height);
    if (Number.isFinite(height)) iframe.style.height = `${{Math.min(Math.max(height, 320), 720)}}px`;
  }});

  document.body.appendChild(iframe);
  document.body.appendChild(button);
}})();
"""

    def _response(self, record: WidgetConfigRecord) -> WidgetConfigResponse:
        return WidgetConfigResponse.model_validate(record.model_dump())
