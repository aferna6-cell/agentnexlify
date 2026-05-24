from pydantic import BaseModel, Field


class AgentControlCenterSummary(BaseModel):
    total_conversations: int = 0
    assisted_conversations: int = 0
    strong_sessions: int = 0
    watch_sessions: int = 0
    at_risk_sessions: int = 0
    active_recovery_queue: int = 0
    lead_capture_rate: float = 0.0
    booking_rate: float = 0.0
    resolved_rate: float = 0.0
    avg_qa_score: float = 0.0
    avg_first_response_seconds: float | None = None
    at_risk_pipeline_value: float = 0.0


class AgentControlCenterScorecard(BaseModel):
    session_id: str
    lead_name: str | None = None
    lead_id: str | None = None
    channel: str = "widget"
    assigned_to: str | None = None
    assigned_to_name: str | None = None
    created_at: str
    last_message_at: str
    message_count: int = 0
    qa_score: int
    qa_status: str
    resolution_status: str
    outcome: str
    first_response_seconds: float | None = None
    intent_signals: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_action: str
    preview: str | None = None
    revenue_won: float = 0.0
    pipeline_value: float = 0.0


class AgentControlCenterRecoveryItem(BaseModel):
    session_id: str
    lead_name: str | None = None
    lead_id: str | None = None
    channel: str = "widget"
    urgency: str
    reason: str
    risk_score: int
    last_customer_message: str | None = None
    last_activity_at: str
    assigned_to: str | None = None
    assigned_to_name: str | None = None
    suggested_playbook: str
    estimated_value: float = 0.0


class AgentControlCenterRoi(BaseModel):
    conversations: int = 0
    assisted: int = 0
    leads_captured: int = 0
    appointments_booked: int = 0
    deals_won: int = 0
    revenue_won: float = 0.0
    pipeline_value: float = 0.0
    at_risk_pipeline_value: float = 0.0
    capture_rate: float = 0.0
    booking_rate: float = 0.0
    win_rate: float = 0.0


class AgentControlCenterResponse(BaseModel):
    period: str
    generated_at: str
    summary: AgentControlCenterSummary
    scorecards: list[AgentControlCenterScorecard] = Field(default_factory=list)
    recovery_queue: list[AgentControlCenterRecoveryItem] = Field(default_factory=list)
    roi: AgentControlCenterRoi
    recommendations: list[str] = Field(default_factory=list)
