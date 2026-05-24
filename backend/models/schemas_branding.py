from pydantic import BaseModel


class BrandingConfig(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    font_family: str | None = None
    widget_title: str | None = None
    powered_by_text: str | None = None
    powered_by_url: str | None = None
    hide_powered_by: bool = False
    custom_css: str | None = None
