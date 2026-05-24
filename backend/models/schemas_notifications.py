from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    type: str  # "new_lead", "new_conversation", "appointment", "activity"
    title: str
    description: str
    created_at: str | None = None


class NotificationsResponse(BaseModel):
    new_leads_count: int = 0
    new_conversations_count: int = 0
    todays_appointments_count: int = 0
    overdue_action_items_count: int = 0
    total_unread: int = 0
    recent_items: list[NotificationItem] = Field(default_factory=list)
