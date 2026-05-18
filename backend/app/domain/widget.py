from pydantic import BaseModel


class WidgetConfig(BaseModel):
    id: str
    display_name: str
    theme: str = "light"
    accent_color: str = "#2563eb"


class EmbedSnippet(BaseModel):
    widget_id: str
    script_tag: str
