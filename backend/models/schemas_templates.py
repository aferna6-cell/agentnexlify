from pydantic import BaseModel, field_validator

VALID_TEMPLATE_CATEGORIES = {"welcome", "follow_up", "reminder", "review", "promotion", "custom"}


class EmailTemplateCreate(BaseModel):
    name: str
    category: str = "custom"
    subject_template: str = ""
    body_template: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_TEMPLATE_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_TEMPLATE_CATEGORIES}")
        return v


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    subject_template: str | None = None
    body_template: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TEMPLATE_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_TEMPLATE_CATEGORIES}")
        return v
