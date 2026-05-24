"""
Re-export shim for backward compatibility.

Pydantic models split into domain modules (`schemas_<domain>.py`) per Rule 9
(don't extend god classes — factor first). Original `schemas.py` reached
999 lines.

Import sites under `backend/routers/*` continue to use
`from backend.models.schemas import X`. Prefer importing from the domain
module directly in new code.
"""
# ruff: noqa: F401, F403

from backend.models.schemas_agent_control import (
    AgentControlCenterRecoveryItem,
    AgentControlCenterResponse,
    AgentControlCenterRoi,
    AgentControlCenterScorecard,
    AgentControlCenterSummary,
)
from backend.models.schemas_appointments import (
    AppointmentListResponse,
    AppointmentOut,
    AppointmentUpdateRequest,
    AvailabilityConfigRequest,
    AvailabilityConfigResponse,
    AvailableSlotsResponse,
    BookAppointmentRequest,
    BookAppointmentResponse,
    DayHours,
    RecurrenceRequest,
    TimeSlot,
)
from backend.models.schemas_auth import (
    GoogleRegisterRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    SignupRequest,
    SignupResponse,
    WidgetConfigDetail,
    WidgetConfigUpdate,
)
from backend.models.schemas_billing import (
    CheckoutResponse,
    CreateCheckoutRequest,
    PortalResponse,
)
from backend.models.schemas_branding import BrandingConfig
from backend.models.schemas_clients import (
    ClientListItem,
    ClientProfile,
    ClientRow,
    ClientUpdateRequest,
    CreateClientRequest,
    CrmDashboardWidgets,
)
from backend.models.schemas_dashboard import (
    DashboardBusinessProfile,
    DashboardQuickAction,
    DashboardResponse,
    LeadScoreResponse,
    ScoreAllResponse,
    TrialStatusResponse,
    WidgetConfigUpdateRequest,
)
from backend.models.schemas_generic import (
    ChatMessageRequest,
    ChatMessageResponse,
    ContactRequest,
    ContactResponse,
    FaqCreateRequest,
    FaqEntryResponse,
)
from backend.models.schemas_leads import (
    VALID_LEAD_STAGES,
    ActivityItem,
    LeadRow,
    LeadStageUpdate,
    LeadUpdateRequest,
    NoteCreateRequest,
    NoteResponse,
    StageChangeRequest,
)
from backend.models.schemas_notifications import (
    NotificationItem,
    NotificationsResponse,
)
from backend.models.schemas_sequences import (
    VALID_TRIGGER_EVENTS,
    AutomationStepCreate,
    SequenceCreateRequest,
    SequenceUpdateRequest,
)
from backend.models.schemas_team import (
    AcceptInviteRequest,
    InviteValidationResponse,
    TeamInviteRequest,
    TeamMemberResponse,
)
from backend.models.schemas_templates import (
    VALID_TEMPLATE_CATEGORIES,
    EmailTemplateCreate,
    EmailTemplateUpdate,
)
from backend.models.schemas_webhooks import (
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookLogResponse,
    WebhookResponse,
    WebhookTestResponse,
    WebhookUpdateRequest,
)
from backend.models.schemas_widget import (
    OnlineStatusRequest,
    WidgetChatRequest,
    WidgetChatResponse,
    WidgetConfigResponse,
    WidgetLeadRequest,
    WidgetLeadResponse,
    WidgetOfflineContactRequest,
)

__all__ = [
    "VALID_LEAD_STAGES",
    "VALID_TRIGGER_EVENTS",
    "VALID_TEMPLATE_CATEGORIES",
    "AcceptInviteRequest",
    "ActivityItem",
    "AgentControlCenterRecoveryItem",
    "AgentControlCenterResponse",
    "AgentControlCenterRoi",
    "AgentControlCenterScorecard",
    "AgentControlCenterSummary",
    "AppointmentListResponse",
    "AppointmentOut",
    "AppointmentUpdateRequest",
    "AutomationStepCreate",
    "AvailabilityConfigRequest",
    "AvailabilityConfigResponse",
    "AvailableSlotsResponse",
    "BookAppointmentRequest",
    "BookAppointmentResponse",
    "BrandingConfig",
    "ChatMessageRequest",
    "ChatMessageResponse",
    "CheckoutResponse",
    "ClientListItem",
    "ClientProfile",
    "ClientRow",
    "ClientUpdateRequest",
    "ContactRequest",
    "ContactResponse",
    "CreateCheckoutRequest",
    "CreateClientRequest",
    "CrmDashboardWidgets",
    "DashboardBusinessProfile",
    "DashboardQuickAction",
    "DashboardResponse",
    "DayHours",
    "EmailTemplateCreate",
    "EmailTemplateUpdate",
    "FaqCreateRequest",
    "FaqEntryResponse",
    "GoogleRegisterRequest",
    "InviteValidationResponse",
    "LeadRow",
    "LeadScoreResponse",
    "LeadStageUpdate",
    "LeadUpdateRequest",
    "LoginRequest",
    "LoginResponse",
    "MeResponse",
    "NotificationItem",
    "NotificationsResponse",
    "NoteCreateRequest",
    "NoteResponse",
    "OnlineStatusRequest",
    "PortalResponse",
    "RecurrenceRequest",
    "RegisterRequest",
    "RegisterResponse",
    "ScoreAllResponse",
    "SequenceCreateRequest",
    "SequenceUpdateRequest",
    "SignupRequest",
    "SignupResponse",
    "StageChangeRequest",
    "TeamInviteRequest",
    "TeamMemberResponse",
    "TimeSlot",
    "TrialStatusResponse",
    "WebhookCreateRequest",
    "WebhookListResponse",
    "WebhookLogResponse",
    "WebhookResponse",
    "WebhookTestResponse",
    "WebhookUpdateRequest",
    "WidgetChatRequest",
    "WidgetChatResponse",
    "WidgetConfigDetail",
    "WidgetConfigResponse",
    "WidgetConfigUpdate",
    "WidgetConfigUpdateRequest",
    "WidgetLeadRequest",
    "WidgetLeadResponse",
    "WidgetOfflineContactRequest",
]
