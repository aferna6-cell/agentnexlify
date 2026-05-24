from pydantic import BaseModel, field_validator

VALID_TRIGGER_EVENTS = {"new_lead", "lead_stage_change", "no_response_24h", "appointment_completed"}


class AutomationStepCreate(BaseModel):
    step_order: int
    delay_minutes: int = 0
    action_type: str = "email"
    subject_template: str = ""
    body_template: str


class SequenceCreateRequest(BaseModel):
    name: str
    trigger_event: str
    trigger_config: dict = {}
    steps: list[AutomationStepCreate]

    @field_validator("trigger_event")
    @classmethod
    def validate_trigger_event(cls, v: str) -> str:
        if v not in VALID_TRIGGER_EVENTS:
            raise ValueError(f"trigger_event must be one of {VALID_TRIGGER_EVENTS}")
        return v


class SequenceUpdateRequest(BaseModel):
    name: str | None = None
    trigger_event: str | None = None
    trigger_config: dict | None = None
    steps: list[AutomationStepCreate] | None = None

    @field_validator("trigger_event")
    @classmethod
    def validate_trigger_event(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TRIGGER_EVENTS:
            raise ValueError(f"trigger_event must be one of {VALID_TRIGGER_EVENTS}")
        return v
