"""Pydantic models for Form & Survey Builder.

Extracted from forms.py (god class split 2026-05-24).
Re-exported via forms.py so existing patches resolve.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

from pydantic import BaseModel, Field


class FormFieldModel(BaseModel):
    id: str = Field(..., max_length=100)
    type: str = Field(..., pattern="^(text|email|phone|textarea|select|radio|checkbox|number|date)$")
    label: str = Field(..., max_length=200)
    required: bool = False
    placeholder: str | None = Field(None, max_length=300)
    options: list[str] | None = None


class FormSettingsModel(BaseModel):
    theme_color: str | None = Field(None, max_length=20)
    submit_button_text: str | None = Field(None, max_length=100)
    show_branding: bool = True


class FormCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    fields_json: list[FormFieldModel] = Field(default_factory=list)
    settings_json: FormSettingsModel | None = None
    redirect_url: str | None = Field(None, max_length=2000)
    success_message: str | None = Field(None, max_length=1000)
    is_active: bool = True


class FormUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    fields_json: list[FormFieldModel] | None = None
    settings_json: FormSettingsModel | None = None
    redirect_url: str | None = Field(None, max_length=2000)
    success_message: str | None = Field(None, max_length=1000)
    is_active: bool | None = None


class PublicFormSubmission(BaseModel):
    data_json: dict = Field(default_factory=dict, max_length=100)
    source_url: str | None = Field(None, max_length=2000)

    def model_post_init(self, __context):
        """Validate data_json size to prevent DoS via oversized payloads."""
        import json
        serialized = json.dumps(self.data_json)
        if len(serialized) > 50_000:  # 50KB max
            raise ValueError("Form submission data too large (max 50KB)")
        if len(self.data_json) > 100:
            raise ValueError("Form submission has too many fields (max 100)")
