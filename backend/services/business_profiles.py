"""Business-type-aware defaults for widgets and dashboard personalization."""

from copy import deepcopy


_TYPE_ALIASES: dict[str, str] = {
    "other": "default",
    "general": "default",
    "default": "default",
    "hvac": "hvac",
    "contractor": "home_services",
    "contractors": "home_services",
    "plumbing": "home_services",
    "electrical": "home_services",
    "roofing": "home_services",
    "landscaping": "home_services",
    "cleaning": "home_services",
    "pest_control": "home_services",
    "painting": "home_services",
    "flooring": "home_services",
    "general_contractor": "home_services",
    "construction": "home_services",
    "moving": "home_services",
    "home_services": "home_services",
    "real_estate": "real_estate",
    "realestate": "real_estate",
    "dental": "dental",
    "medical": "medical",
    "health_wellness": "medical",
    "healthcare": "medical",
    "clinic": "medical",
    "doctor": "medical",
    "chiropractic": "medical",
    "veterinary": "medical",
    "salon": "salon",
    "spa": "salon",
    "beauty": "salon",
    "barber": "salon",
    "restaurant": "restaurant",
    "bakery": "restaurant",
    "bar_nightclub": "restaurant",
    "cafe": "restaurant",
    "catering": "restaurant",
    "food_truck": "restaurant",
    "legal": "legal",
    "accounting": "professional_services",
    "professional": "professional_services",
    "professional_services": "professional_services",
    "consulting": "professional_services",
    "photography": "professional_services",
    "tutoring": "professional_services",
    "auto_shop": "auto_shop",
    "automotive": "auto_shop",
    "mechanic": "auto_shop",
    "auto_detailing": "auto_shop",
    "auto_detailer": "auto_shop",
    "fitness": "fitness",
    "retail": "retail",
}


def humanize_business_type(business_type: str | None) -> str:
    raw = (business_type or "").strip().replace("_", " ")
    if not raw:
        return "Business"
    special = {"hvac": "HVAC", "spa": "Spa"}
    lower = raw.lower()
    if lower in special:
        return special[lower]
    return " ".join(word.capitalize() for word in raw.split())


def resolve_business_profile_key(business_type: str | None) -> str:
    normalized = (business_type or "").strip().lower()
    if not normalized:
        return "default"
    return _TYPE_ALIASES.get(normalized, normalized if normalized in _BUSINESS_PROFILES else "default")


_BASE_PROFILE = {
    "key": "default",
    "headline": "Run a tailored dashboard without giving up a flexible platform",
    "subheadline": "AgentNexLiFy keeps the core engine broad, then shapes your dashboard, messaging, and next steps around your business type.",
    "focus_areas": ["Leads", "Conversations", "Automations"],
    "conversation_label": "Conversations This Month",
    "conversation_empty_hint": "Set up your widget to start capturing conversations",
    "lead_label": "Leads Captured",
    "lead_empty_hint": "Leads appear automatically from widget chats",
    "automation_label": "Automations Active",
    "automation_empty_hint": "Set up your first automation",
    "appointment_label": "Appointments This Week",
    "missed_call_label": "Missed Calls This Week",
    "missed_call_empty_hint": "Enable missed call text-back in Settings",
    "proof_metric_label": "Customer opportunities captured",
    "proof_metric_empty_hint": "Your proof metric appears once customers start chatting",
    "widget": {
        "bot_name_suffix": "Assistant",
        "primary_color": "#00BFFF",
        "greeting_template": "Hi! Welcome to {business_name}. How can I help you today?",
        "position": "bottom-right",
    },
    "quick_actions": [
        {
            "label": "Quick Book",
            "description": "Book an appointment now",
            "action": "book",
        },
        {
            "label": "Add Lead",
            "description": "Manually add a new lead",
            "action": "lead",
        },
        {
            "label": "Send Campaign",
            "description": "Launch a follow-up or nurture flow",
            "action": "navigate",
            "page": "automations",
        },
        {
            "label": "View Conversations",
            "description": "See active customer chats",
            "action": "navigate",
            "page": "conversations",
        },
    ],
}


_BUSINESS_PROFILES: dict[str, dict] = {
    "default": deepcopy(_BASE_PROFILE),
    "hvac": {
        **deepcopy(_BASE_PROFILE),
        "key": "hvac",
        "headline": "Stay on top of HVAC calls, quotes, and booked jobs",
        "subheadline": "Prioritize urgent service requests, keep missed-call follow-up tight, and move estimates to booked work faster.",
        "focus_areas": ["Missed Calls", "Quotes", "Booked Jobs"],
        "conversation_label": "Customer Conversations",
        "conversation_empty_hint": "Share your widget and phone line to start capturing repair and install requests",
        "lead_label": "Service Leads",
        "lead_empty_hint": "New repair, maintenance, and install leads show up here automatically",
        "automation_label": "Follow-Ups Live",
        "automation_empty_hint": "Turn on estimate and reminder automations",
        "appointment_label": "Jobs Booked This Week",
        "missed_call_label": "Missed Service Calls",
        "proof_metric_label": "Service opportunities captured",
        "proof_metric_empty_hint": "New repair, maintenance, and install requests will count here",
        "widget": {
            "bot_name_suffix": "Dispatch",
            "primary_color": "#f97316",
            "greeting_template": "Hi! Thanks for contacting {business_name}. Do you need AC repair, heating service, or an estimate for a new system?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Job", "description": "Schedule a service visit", "action": "book"},
            {"label": "Add Service Lead", "description": "Log a phone or web inquiry", "action": "lead"},
            {"label": "Open Pipeline", "description": "Move estimates and jobs forward", "action": "navigate", "page": "pipeline"},
            {"label": "Review Calls", "description": "Check missed calls and callbacks", "action": "navigate", "page": "calls"},
        ],
    },
    "home_services": {
        **deepcopy(_BASE_PROFILE),
        "key": "home_services",
        "headline": "Keep home-service leads moving from inquiry to booked work",
        "subheadline": "Track calls, quotes, and appointments in one place without losing the flexibility to fit your specific trade.",
        "focus_areas": ["Leads", "Pipeline", "Bookings"],
        "conversation_label": "Customer Conversations",
        "lead_label": "Service Leads",
        "lead_empty_hint": "Phone and website inquiries will land here as new service leads",
        "automation_label": "Follow-Ups Live",
        "automation_empty_hint": "Set up quote reminders and lead follow-ups",
        "appointment_label": "Jobs Booked This Week",
        "missed_call_label": "Missed Job Calls",
        "proof_metric_label": "Quote-ready jobs captured",
        "proof_metric_empty_hint": "Estimate requests and urgent service leads will count here",
        "widget": {
            "bot_name_suffix": "Scheduling Desk",
            "primary_color": "#0f766e",
            "greeting_template": "Hi! Thanks for contacting {business_name}. What kind of service do you need today?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Job", "description": "Schedule a visit or estimate", "action": "book"},
            {"label": "Add Service Lead", "description": "Create a new inquiry manually", "action": "lead"},
            {"label": "Open Pipeline", "description": "Track estimates and won jobs", "action": "navigate", "page": "pipeline"},
            {"label": "View Conversations", "description": "Review active customer chats", "action": "navigate", "page": "conversations"},
        ],
    },
    "real_estate": {
        **deepcopy(_BASE_PROFILE),
        "key": "real_estate",
        "headline": "Manage buyer and seller inquiries with a real-estate-first view",
        "subheadline": "Keep showing requests, lead nurture, and pipeline progress front and center for your team.",
        "focus_areas": ["Buyer Leads", "Showings", "Nurture"],
        "lead_label": "Buyer & Seller Leads",
        "lead_empty_hint": "New buyer and seller inquiries will appear here automatically",
        "automation_label": "Nurtures Live",
        "automation_empty_hint": "Launch follow-up sequences for new prospects",
        "appointment_label": "Showings This Week",
        "proof_metric_label": "Buyer and seller opportunities captured",
        "widget": {
            "bot_name_suffix": "Lead Desk",
            "primary_color": "#2563eb",
            "greeting_template": "Hi! Welcome to {business_name}. Are you looking to buy, sell, or schedule a showing?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Showing", "description": "Schedule a showing or consult", "action": "book"},
            {"label": "Add Buyer/Seller Lead", "description": "Log a new prospect", "action": "lead"},
            {"label": "Lead Nurture", "description": "Open follow-up automations", "action": "navigate", "page": "automations"},
            {"label": "Open Pipeline", "description": "Track leads through close", "action": "navigate", "page": "pipeline"},
        ],
    },
    "dental": {
        **deepcopy(_BASE_PROFILE),
        "key": "dental",
        "headline": "Keep patient inquiries, reminders, and booked visits organized",
        "subheadline": "Use patient-friendly defaults without losing the flexibility to customize your practice workflow.",
        "focus_areas": ["New Patients", "Appointments", "Reminders"],
        "lead_label": "Patient Leads",
        "lead_empty_hint": "New patient chats and forms will appear here automatically",
        "automation_label": "Reminders Live",
        "automation_empty_hint": "Enable reminders and recall sequences",
        "proof_metric_label": "New patient inquiries captured",
        "proof_metric_empty_hint": "New patient questions and appointment requests will count here",
        "widget": {
            "bot_name_suffix": "Front Desk",
            "primary_color": "#0ea5e9",
            "greeting_template": "Hi! Thanks for contacting {business_name}. Are you booking a cleaning, asking about treatment, or looking for a new patient appointment?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Visit", "description": "Schedule a patient appointment", "action": "book"},
            {"label": "Add Patient Lead", "description": "Create a new patient inquiry", "action": "lead"},
            {"label": "Open Calendar", "description": "Review upcoming visits", "action": "navigate", "page": "calendar"},
            {"label": "Send Reminders", "description": "Open automations and sequences", "action": "navigate", "page": "automations"},
        ],
    },
    "medical": {
        **deepcopy(_BASE_PROFILE),
        "key": "medical",
        "headline": "Keep patient communications and bookings aligned around care",
        "subheadline": "Start with medical-friendly copy and workflow priorities, then customize from there.",
        "focus_areas": ["Patients", "Bookings", "Follow-Up"],
        "lead_label": "Patient Leads",
        "automation_label": "Follow-Ups Live",
        "proof_metric_label": "Patient inquiries captured",
        "proof_metric_empty_hint": "Appointment and patient questions will count here",
        "widget": {
            "bot_name_suffix": "Care Desk",
            "primary_color": "#14b8a6",
            "greeting_template": "Hi! Thanks for contacting {business_name}. How can we help with your appointment or patient question today?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Visit", "description": "Schedule an appointment", "action": "book"},
            {"label": "Add Patient Lead", "description": "Create a patient inquiry", "action": "lead"},
            {"label": "Open Calendar", "description": "Review the schedule", "action": "navigate", "page": "calendar"},
            {"label": "View Conversations", "description": "Check recent patient messages", "action": "navigate", "page": "conversations"},
        ],
    },
    "salon": {
        **deepcopy(_BASE_PROFILE),
        "key": "salon",
        "headline": "Keep bookings, repeat clients, and follow-up offers visible",
        "subheadline": "AgentNexLiFy starts with salon-friendly defaults so your dashboard feels ready on day one.",
        "focus_areas": ["Bookings", "Clients", "Repeat Visits"],
        "lead_label": "Client Leads",
        "appointment_label": "Bookings This Week",
        "proof_metric_label": "Booking inquiries captured",
        "proof_metric_empty_hint": "Service, pricing, and availability questions will count here",
        "widget": {
            "bot_name_suffix": "Booking Desk",
            "primary_color": "#db2777",
            "greeting_template": "Hi! Welcome to {business_name}. Are you booking a service, asking about availability, or checking pricing?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Appointment", "description": "Schedule a new visit", "action": "book"},
            {"label": "Add Client Lead", "description": "Add a new inquiry", "action": "lead"},
            {"label": "Open Calendar", "description": "Review upcoming bookings", "action": "navigate", "page": "calendar"},
            {"label": "Send Promotion", "description": "Open marketing automations", "action": "navigate", "page": "automations"},
        ],
    },
    "restaurant": {
        **deepcopy(_BASE_PROFILE),
        "key": "restaurant",
        "headline": "Handle reservations and inquiries with a restaurant-friendly starting point",
        "subheadline": "Keep bookings, private-event leads, and customer conversations visible without rebuilding the app for a new vertical.",
        "focus_areas": ["Reservations", "Catering", "Guests"],
        "lead_label": "Guest Leads",
        "appointment_label": "Reservations This Week",
        "proof_metric_label": "Reservation and event inquiries captured",
        "widget": {
            "bot_name_suffix": "Host Stand",
            "primary_color": "#b45309",
            "greeting_template": "Hi! Welcome to {business_name}. Are you looking to book a table, ask about catering, or place an order?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Reservation", "description": "Schedule a table or event", "action": "book"},
            {"label": "Add Guest Lead", "description": "Log a catering or event inquiry", "action": "lead"},
            {"label": "View Conversations", "description": "Review customer chats", "action": "navigate", "page": "conversations"},
            {"label": "Open Automations", "description": "Launch follow-up campaigns", "action": "navigate", "page": "automations"},
        ],
    },
    "legal": {
        **deepcopy(_BASE_PROFILE),
        "key": "legal",
        "headline": "Keep new matters and consultations organized from the first inquiry",
        "subheadline": "Start with intake-first defaults for law firms, then tune the workflow around your practice areas.",
        "focus_areas": ["Intake", "Consultations", "Follow-Up"],
        "lead_label": "New Matters",
        "appointment_label": "Consultations This Week",
        "proof_metric_label": "Potential matters captured",
        "widget": {
            "bot_name_suffix": "Intake Desk",
            "primary_color": "#1d4ed8",
            "greeting_template": "Hi! Thanks for contacting {business_name}. Are you looking to schedule a consultation or ask about a legal matter?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Consultation", "description": "Schedule a consult", "action": "book"},
            {"label": "Add Matter", "description": "Create a new intake lead", "action": "lead"},
            {"label": "Open Pipeline", "description": "Track retained and active cases", "action": "navigate", "page": "pipeline"},
            {"label": "View Conversations", "description": "Review new inquiries", "action": "navigate", "page": "conversations"},
        ],
    },
    "auto_shop": {
        **deepcopy(_BASE_PROFILE),
        "key": "auto_shop",
        "headline": "Track repair inquiries, appointments, and follow-up work in one view",
        "subheadline": "Use auto-shop-ready defaults for your front desk while keeping the platform broad underneath.",
        "focus_areas": ["Repair Leads", "Appointments", "Callbacks"],
        "lead_label": "Repair Leads",
        "appointment_label": "Service Visits This Week",
        "proof_metric_label": "Vehicle service requests captured",
        "proof_metric_empty_hint": "Repair, maintenance, and quote requests will count here",
        "widget": {
            "bot_name_suffix": "Service Desk",
            "primary_color": "#374151",
            "greeting_template": "Hi! Thanks for contacting {business_name}. What vehicle issue or service do you need help with today?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Service", "description": "Schedule a repair visit", "action": "book"},
            {"label": "Add Repair Lead", "description": "Log a new vehicle inquiry", "action": "lead"},
            {"label": "Open Calendar", "description": "Review the shop schedule", "action": "navigate", "page": "calendar"},
            {"label": "Open Pipeline", "description": "Track quotes and jobs", "action": "navigate", "page": "pipeline"},
        ],
    },
    "fitness": {
        **deepcopy(_BASE_PROFILE),
        "key": "fitness",
        "headline": "Keep trial leads, consultations, and member follow-up visible",
        "subheadline": "Use fitness-friendly defaults to turn inquiries into booked consults and long-term members.",
        "focus_areas": ["Trials", "Consults", "Retention"],
        "lead_label": "Member Leads",
        "appointment_label": "Consults This Week",
        "proof_metric_label": "Trial and membership inquiries captured",
        "widget": {
            "bot_name_suffix": "Member Desk",
            "primary_color": "#16a34a",
            "greeting_template": "Hi! Welcome to {business_name}. Are you interested in a membership, class schedule, or personal training?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Consult", "description": "Schedule an intro session", "action": "book"},
            {"label": "Add Member Lead", "description": "Log a new prospect", "action": "lead"},
            {"label": "Open Calendar", "description": "Review upcoming sessions", "action": "navigate", "page": "calendar"},
            {"label": "Open Automations", "description": "Launch nurture sequences", "action": "navigate", "page": "automations"},
        ],
    },
    "professional_services": {
        **deepcopy(_BASE_PROFILE),
        "key": "professional_services",
        "headline": "Start with service-business defaults and refine from there",
        "subheadline": "Keep the platform broad underneath while giving service-led teams a more relevant first dashboard.",
        "focus_areas": ["Leads", "Follow-Up", "Pipeline"],
        "proof_metric_label": "Client opportunities captured",
        "widget": {
            "bot_name_suffix": "Client Desk",
            "primary_color": "#4338ca",
            "greeting_template": "Hi! Thanks for contacting {business_name}. How can we help with your inquiry today?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Book Consult", "description": "Schedule an intro call", "action": "book"},
            {"label": "Add Client Lead", "description": "Create a new inquiry", "action": "lead"},
            {"label": "Open Pipeline", "description": "Track opportunities", "action": "navigate", "page": "pipeline"},
            {"label": "View Conversations", "description": "Review recent messages", "action": "navigate", "page": "conversations"},
        ],
    },
    "retail": {
        **deepcopy(_BASE_PROFILE),
        "key": "retail",
        "headline": "Start with a retail-friendly dashboard while keeping the core platform broad",
        "subheadline": "Prioritize customer questions, promotions, and order-related follow-up without boxing the product into one narrow use case.",
        "focus_areas": ["Customers", "Orders", "Promotions"],
        "lead_label": "Customer Leads",
        "proof_metric_label": "Customer inquiries captured",
        "widget": {
            "bot_name_suffix": "Support Desk",
            "primary_color": "#7c3aed",
            "greeting_template": "Hi! Welcome to {business_name}. Can we help with a product question, an order, or store information?",
            "position": "bottom-right",
        },
        "quick_actions": [
            {"label": "Add Customer Lead", "description": "Create a new customer inquiry", "action": "lead"},
            {"label": "View Conversations", "description": "Review customer questions", "action": "navigate", "page": "conversations"},
            {"label": "Open Automations", "description": "Launch campaigns and follow-up", "action": "navigate", "page": "automations"},
            {"label": "Open Dashboard", "description": "Stay on top of activity", "action": "navigate", "page": "dashboard"},
        ],
    },
}


def get_widget_defaults(business_type: str | None, business_name: str | None) -> dict[str, str]:
    """Return widget defaults for the given business type."""
    profile = _BUSINESS_PROFILES[resolve_business_profile_key(business_type)]
    widget = profile["widget"]
    safe_name = (business_name or "Your Business").strip() or "Your Business"
    return {
        "bot_name": f"{safe_name} {widget['bot_name_suffix']}".strip(),
        "primary_color": widget["primary_color"],
        "greeting_message": widget["greeting_template"].format(business_name=safe_name),
        "position": widget["position"],
    }


def get_dashboard_business_profile(business_type: str | None, business_name: str | None) -> dict:
    """Return a dashboard-facing preset summary for a tenant."""
    key = resolve_business_profile_key(business_type)
    profile = deepcopy(_BUSINESS_PROFILES[key])
    profile.pop("widget", None)
    profile["label"] = humanize_business_type(business_type) if business_type else humanize_business_type(key)
    return profile

