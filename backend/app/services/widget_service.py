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
        normalized_origin = self._normalize_origin(request_origin)
        if record.allowed_origins and normalized_origin not in self._normalized_allowed_origins(record.allowed_origins):
            raise PermissionDenied(
                f"Origin {normalized_origin or 'unknown'} is not allowed for this widget."
            )
        return PublicWidgetConfigResponse(
            widget_id=record.widget_id,
            theme=record.theme,
            greeting=record.greeting,
            enabled_tools=record.enabled_tools,
        )

    async def get_frame_html(
        self,
        widget_id: str,
        *,
        request_origin: str | None,
        widget_public_url: str,
        api_base: str,
        host_origin: str | None,
    ) -> tuple[str, str]:
        record = await self.repository.get_config(widget_id)
        if record is None:
            raise NotFoundError("Widget config not found.")
        normalized_origin = self._normalize_origin(request_origin)
        if record.allowed_origins and normalized_origin not in self._normalized_allowed_origins(record.allowed_origins):
            raise PermissionDenied(
                f"Origin {normalized_origin or 'unknown'} is not allowed for this widget."
            )

        widget_src = (
            f"{widget_public_url.rstrip('/')}/"
            f"?widgetId={quote(widget_id)}"
            f"&apiBase={quote(api_base.rstrip('/'), safe=':/')}"
            f"&hostOrigin={quote(host_origin or request_origin or '')}"
        )
        html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Maintainers Copilot</title>
    <style>
      html, body, iframe {{
        width: 100%;
        height: 100%;
        margin: 0;
        border: 0;
        overflow: hidden;
      }}
      body {{ background: transparent; }}
    </style>
  </head>
  <body>
    <iframe title="Maintainers Copilot" src="{widget_src}" allow="clipboard-write"></iframe>
    <script>
      window.addEventListener("message", (event) => {{
        if (event.data?.type === "widget:resize") {{
          window.parent.postMessage(event.data, "*");
        }}
      }});
    </script>
  </body>
</html>
"""
        return html, self._frame_ancestors(record.allowed_origins)

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
  const frameUrl = new URL(`/widget/frame/${{encodeURIComponent(widgetId)}}`, apiBase);
  frameUrl.searchParams.set("widgetUrl", widgetBase);
  frameUrl.searchParams.set("apiBase", apiBase);
  frameUrl.searchParams.set("hostOrigin", hostOrigin);
  const button = document.createElement("button");
  button.type = "button";
  button.id = "maintainers-copilot-launcher";
  button.className = "maintainers-copilot-launcher";
  button.textContent = script?.dataset.label || "Ask Maintainers Copilot";
  button.setAttribute("aria-expanded", "false");
  button.style.cssText = [
    "position:fixed",
    "right:24px",
    "bottom:24px",
    "z-index:2147483647",
    "border:1px solid rgba(255,255,255,.14)",
    "border-radius:999px",
    "padding:12px 16px",
    "background:#0b1220",
    "color:#fff",
    "font:700 14px system-ui,sans-serif",
    "box-shadow:0 16px 38px rgba(15,23,42,.28)",
    "cursor:pointer"
  ].join(";");

  const iframe = document.createElement("iframe");
  iframe.title = "Maintainers Copilot";
  iframe.id = `maintainers-copilot-frame-${{widgetId}}`;
  iframe.src = frameUrl.toString();
  iframe.style.cssText = [
    "position:fixed",
    "right:24px",
    "bottom:78px",
    "z-index:2147483647",
    "width:430px",
    "height:640px",
    "max-width:calc(100vw - 32px)",
    "border:0",
    "border-radius:8px",
    "box-shadow:0 24px 70px rgba(15,23,42,.32)",
    "display:none",
    "background:#fff"
  ].join(";");

  function setOpen(open) {{
    iframe.style.display = open ? "block" : "none";
    button.setAttribute("aria-expanded", String(open));
    button.textContent = open ? "Close copilot" : (script?.dataset.label || "Ask Maintainers Copilot");
  }}

  window.MaintainersCopilot = Object.assign(window.MaintainersCopilot || {{}}, {{
    open: () => setOpen(true),
    close: () => setOpen(false),
    toggle: () => setOpen(iframe.style.display === "none"),
  }});

  button.addEventListener("click", window.MaintainersCopilot.toggle);

  window.addEventListener("message", (event) => {{
    if (event.data?.type !== "widget:resize") return;
    const height = Number(event.data.height);
    if (Number.isFinite(height)) iframe.style.height = `${{Math.min(Math.max(height, 320), 720)}}px`;
  }});

  document.body.appendChild(iframe);
  document.body.appendChild(button);
}})();
"""


    def _normalize_origin(self, origin: str | None) -> str | None:
        if not origin:
            return None
        value = origin.strip().rstrip("/")
        if not value:
            return None
        try:
            from urllib.parse import urlparse

            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                return value
            hostname = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            return f"{parsed.scheme.lower()}://{hostname.lower()}{port}"
        except ValueError:
            return value

    def _normalized_allowed_origins(self, allowed_origins: list[str]) -> set[str | None]:
        return {self._normalize_origin(origin) for origin in allowed_origins}

    def _frame_ancestors(self, allowed_origins: list[str]) -> str:
        if not allowed_origins:
            return "frame-ancestors 'self'"
        return "frame-ancestors " + " ".join(allowed_origins)

    def _response(self, record: WidgetConfigRecord) -> WidgetConfigResponse:
        return WidgetConfigResponse.model_validate(record.model_dump())
