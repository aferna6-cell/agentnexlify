# Graph Report - /home/aidan/agentnexlify  (2026-04-06)

## Corpus Check
- 550 files · ~685,234 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4174 nodes · 6252 edges · 219 communities detected
- Extraction: 68% EXTRACTED · 31% INFERRED · 0% AMBIGUOUS · INFERRED: 1953 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `MockSupabaseTable` - 59 edges
2. `MockSupabaseClient` - 43 edges
3. `MockSupabaseResponse` - 41 edges
4. `LeadScoreResponse` - 29 edges
5. `ScoreAllResponse` - 29 edges
6. `LeadUpdateRequest` - 29 edges
7. `Architecture Decisions` - 26 edges
8. `_mock_db()` - 23 edges
9. `AvailabilityConfigRequest` - 23 edges
10. `AvailabilityConfigResponse` - 23 edges

## Surprising Connections (you probably didn't know these)
- `python-jose[cryptography]` --implements--> `FastAPI Backend Service`  [INFERRED]
  backend/requirements.txt → CLAUDE.md
- `bcrypt>=4.0.0` --implements--> `FastAPI Backend Service`  [INFERRED]
  backend/requirements.txt → CLAUDE.md
- `slowapi==0.1.9` --implements--> `FastAPI Backend Service`  [INFERRED]
  backend/requirements.txt → CLAUDE.md
- `Google Auth Libraries` --implements--> `FastAPI Backend Service`  [INFERRED]
  backend/requirements.txt → CLAUDE.md
- `Email Drip Sequences` --PRECEDES--> `Feature: Guided Onboarding Wizard (P0)`  [INFERRED]
  /home/aidan/agentnexlify/docs/daily-logs/2026-03-31.md → /home/aidan/agentnexlify/knowledge-base/wiki/growth/post-launch-growth-strategy.md

## Hyperedges (group relationships)
- **** — git_hooks, github_actions, claude_code_hooks, morning_routine, evening_routine, ai_auto_improve_report, kairos_agent [INFERRED 0.85]
- **** — claude_md, agents_md, gemini_md, ai_manifest, agent_system_plan [EXTRACTED 1.00]
- **** — audit_results_v2, full_audit, pre_launch_audit, codebase_audit_2026_03_25, cleanup_report [INFERRED 0.90]
- **Council Consensus: Stop Building, Start Selling** —  [INFERRED 0.95]
- **Council Consensus: Home Services Wedge** —  [EXTRACTED 1.00]
- **P0 Growth Features (Do First)** —  [EXTRACTED 1.00]
- **P1 Growth Features (Do Next)** —  [EXTRACTED 1.00]
- **MTOptions Triage Issues** —  [EXTRACTED 1.00]
- **Cross-Industry Open Gaps (Affect All Verticals)** —  [EXTRACTED 1.00]
- **Strongest Product-Market Fit Verticals** —  [EXTRACTED 1.00]
- **Five-Workspace Architecture** —  [EXTRACTED 1.00]
- **Generated Visualization Skills** —  [INFERRED 0.90]
- **Direct Competitive Threats** —  [EXTRACTED 0.95]
- **Council Decision Arc (Apr 1-3 2026)** —  [EXTRACTED 1.00]
- **Feature Velocity Timeline (Mar 12 - Apr 05)** — log_2026_03_12, log_2026_03_13, log_2026_03_15, log_2026_03_18, log_2026_03_20, log_2026_03_21, log_2026_03_23, log_2026_04_01, log_2026_04_03 [INFERRED 0.85]
- **Recurring Bug: conversations client_id vs tenant_id (3+ occurrences)** — bug_client_id_regression, log_2026_03_20, log_2026_03_23, log_2026_03_24 [EXTRACTED 0.95]
- **Migration Discipline Erosion (065-079 pending across 11+ days)** — issue_migration_backlog, issue_duplicate_migrations, issue_pending_migrations_077_079, log_2026_03_23, log_2026_03_27, log_2026_03_30, log_2026_03_31, log_2026_04_01, log_2026_04_02, log_2026_04_03 [EXTRACTED 0.95]
- **Hotspot -> Decision -> Refactor Cycle (api.js, widget.py)** — hotspot_api_js, hotspot_main_py, decision_api_js_split, decision_widget_split, feature_api_js_split, feature_widget_split, refactor_api_js_monolith_deleted [INFERRED 0.90]
- **Chat Widget Request Flow** — claudemd_chat_widget, claudemd_fastapi_backend, claudemd_claude_api, claudemd_supabase_database, claudemd_twilio_sms [EXTRACTED 1.00]
- **Multi-Tenant Data Isolation Pattern** — claudemd_multi_tenant_architecture, claudemd_rls_policy, claudemd_client_id_rule, claudemd_schema_discipline, claudemd_tenants_table [EXTRACTED 1.00]
- **Third-Party Integration Layer** — claudemd_stripe_payments, claudemd_resend_email, claudemd_twilio_sms, claudemd_claude_api, requirements_google_auth [EXTRACTED 0.90]
- **NEXUS-Full Pipeline: 7 phases across all divisions** — product_division, project_management_division, design_division, engineering_division, testing_division, marketing_division, support_division [INFERRED]
- **Startup MVP Workflow: 7 agents from 4 divisions collaborate** — product_division, design_division, engineering_division, testing_division [INFERRED]
- **Nexus Spatial Discovery: 8 agents from 8 divisions in parallel** — product_division, engineering_division, design_division, marketing_division, support_division, project_management_division, spatial_computing_division [INFERRED]
- **Marketing Campaign Workflow: marketing + design + support collaborate** — marketing_division, design_division, support_division, paid_media_division [INFERRED]
- **** — bug_client_id_tenant_id, bug_lead_stage_status, bug_field_name_mismatch, bug_knowledge_base_null [INFERRED 0.90]
- **** — bug_silent_except, bug_base_exception, bug_conversations_rls, bug_no_response_dedup [INFERRED 0.90]
- **** — bug_n_plus_1, bug_campaign_blocking, bug_anthropic_timeout [INFERRED 0.85]
- **** — industry_salon, industry_dental, industry_plumber, industry_restaurant [EXTRACTED 0.95]
- **** — industry_fitness, industry_lawyer, industry_real_estate [EXTRACTED 0.90]
- **** — onboarding_welcome, onboarding_day1, onboarding_day3, onboarding_day7, onboarding_day14 [EXTRACTED 1.00]
- **** — adr_all_in_one_platform, adr_multi_tenant, adr_agency_architecture, adr_background_automation_loop [INFERRED 0.90]
- **** — pain_after_hours, pain_slow_followup, pain_no_shows, pain_missed_calls, pain_contact_forms [EXTRACTED 1.00]

## Communities

### Community 0 - "Auth & Session Management"
Cohesion: 0.01
Nodes (244): ABTestCreate, ABTestUpdate, ABTestVariantCreate, ABTestVariantUpdate, _assign_lead_to_variant(), _calculate_significance(), complete_ab_test(), create_ab_test() (+236 more)

### Community 1 - "CRM Action Items & Notes"
Cohesion: 0.01
Nodes (41): action_items_summary(), ActionItemCreate, ActionItemUpdate, create_action_item(), delete_action_item(), list_action_items(), Action items CRUD — AI-extracted tasks from conversations., Create an action item manually. (+33 more)

### Community 2 - "Test Infrastructure"
Cohesion: 0.02
Nodes (128): Bug: Analytics 0 Conversations (FK to Legacy Table), Bug: API client 204 handling, Bug: conversations uses client_id not tenant_id, Bug: conversations FK to legacy clients table, Bug: dict.get returns None for NULL, Bug: International Phone Capture Regex, Bug: Python or/== operator precedence, Bug: Twilio Signature Validation Bypass (+120 more)

### Community 3 - "Automation Rules Engine"
Cohesion: 0.03
Nodes (109): Agent System Plan, AgentNexLiFy Platform, AGENTS.md Codex Adapter, AI Architecture Audit, AI Auto Improve Report, AI Development System, .ai/manifest.json Machine Index, Anti-Desperation Error Philosophy (+101 more)

### Community 4 - "Lead Management"
Cohesion: 0.04
Nodes (66): _clear_widget_cache(), mock_settings(), mock_supabase(), MockSupabaseClient, MockSupabaseResponse, MockSupabaseTable, Shared test fixtures for AgentNexLiFy tests., Provide a mock Supabase client and patch get_supabase. (+58 more)

### Community 5 - "Automation Execution Engine"
Cohesion: 0.03
Nodes (88): ADR: Multi-tenant agency architecture, ADR: All-in-one platform not separate products, ADR: api.js split into 35 domain modules, ADR: 9 tasks in one automation loop, ADR: Chat flow via prompt injection, ADR: chat_messages as canonical store, ADR: AI-estimated competitor scores, ADR: Single Claude call for all platform versions (+80 more)

### Community 6 - "Invoicing & Billing"
Cohesion: 0.05
Nodes (21): AutonomousImprover, main(), EvaluationEngine, main(), _split_csv(), main(), PatternExtractor, main() (+13 more)

### Community 7 - "Appointment Booking"
Cohesion: 0.11
Nodes (67): billing_cancel(), billing_change_plan(), billing_checkout(), billing_portal(), _compute_trial_status(), _create_token(), dashboard(), _decode_google_setup_token() (+59 more)

### Community 8 - "Widget Chat Engine"
Cohesion: 0.03
Nodes (74): Bug: Chat Endpoint 404 (Invalid Model ID), Bug: conversations client_id Regression, Bug: Form Submission DoS, Bug: markInvoicePaid 422 (No Body), Bug: N+1 in CSV Lead Import, Bug: Pipeline Drag-Drop 422, Bug: FastAPI Route Shadowing, Bug: Smart Lists Filter Key Mismatch (+66 more)

### Community 9 - "Automation Engine Tests"
Cohesion: 0.06
Nodes (49): assign_lead(), AssignLeadRequest, bulk_update_leads(), BulkUpdateRequest, create_lead(), debug_lead_capture(), export_leads_csv(), find_duplicate_leads() (+41 more)

### Community 10 - "Local SEO & GEO Scoring"
Cohesion: 0.04
Nodes (67): _advance_execution(), check_appointment_triggers(), check_form_submission_triggers(), check_lead_captured_triggers(), check_new_reviews(), check_no_response_leads(), check_tag_triggers(), _evaluate_conditions() (+59 more)

### Community 11 - "Analytics Dashboard"
Cohesion: 0.04
Nodes (49): _build_invoice_email_html(), bulk_send_invoices(), BulkSendRequest, _compute_invoice_totals(), create_invoice(), create_invoice_from_bid(), create_item_template(), delete_invoice() (+41 more)

### Community 12 - "Router CRUD Tests"
Cohesion: 0.13
Nodes (48): book_appointment(), create_service_type(), dashboard_book_appointment(), _DashboardBookBody, delete_appointment(), delete_service_type(), get_appointments(), get_availability() (+40 more)

### Community 13 - "Business Page Tests"
Cohesion: 0.04
Nodes (58): Backend Known Issues, backend/main.py Entry Point, Backend Routers (53 files), Pydantic Models (schemas.py), Backend Services Layer, 4 Uvicorn Workers (Production), AgentNexLiFy Platform, Appointments Table (+50 more)

### Community 14 - "Auth & Billing Routes"
Cohesion: 0.05
Nodes (51): _build_conversation_summary(), _build_flow_instructions(), _build_intent_window(), _build_system_prompt(), _capture_leads_from_session(), _categorize_conversation(), _compact_messages_for_llm(), _extract_action_items() (+43 more)

### Community 15 - "Form Builder"
Cohesion: 0.04
Nodes (26): _make_db_mock(), Tests for the automation engine service.  Covers: process_pending_steps, send_in, Tests for trigger_sequence()., Tests for send_invoice_payment_reminders()., Return a (db, table) pair where every chained Supabase call returns the     same, Tests for send_weekly_intelligence_briefs().      The function imports `settings, Tests for process_pending_steps()., Shared-state query mock for recurring invoice workflow tests. (+18 more)

### Community 16 - "Bid & Estimate System"
Cohesion: 0.06
Nodes (51): _analyze_keywords_ai(), analyze_seo_profile(), _calculate_completeness(), calculate_geo_score(), CompetitorRequest, DashboardWidgetResponse, _generate_keywords(), GEOScoreRequest (+43 more)

### Community 17 - "Marketing Tests"
Cohesion: 0.07
Nodes (38): analytics_health(), _build_control_center_recommendations(), _clamp_score(), _date_range(), _first_response_seconds(), get_agent_control_center(), get_ai_insights(), _get_cached() (+30 more)

### Community 18 - "Lead Extraction Tests"
Cohesion: 0.08
Nodes (37): _auth(), _make_token(), _mock_db(), Tests for previously untested CRUD routers.  Covers: snippets, tag_definitions,, test_create_automation(), test_create_bid(), test_create_field(), test_create_scoring_factor() (+29 more)

### Community 19 - "Documents & E-Signatures"
Cohesion: 0.05
Nodes (37): add_step(), create_sequence(), delete_sequence(), delete_step(), _enroll_lead(), enroll_lead_in_sequences(), EnrollRequest, get_sequence() (+29 more)

### Community 20 - "Community 20"
Cohesion: 0.05
Nodes (20): http_client(), Tests for business page endpoints — public page + dashboard settings., Test the data mapping for the public business page., Configure db_mock.table() to return different data per table name., Create a FastAPI TestClient with mocked Supabase for endpoint tests., Integration tests for GET /biz/{slug} endpoint., GET /biz/{slug} with a valid, enabled slug returns 200 with page data., GET /biz/{slug} with a slug that does not exist returns 404. (+12 more)

### Community 21 - "Community 21"
Cohesion: 0.05
Nodes (34): create_form(), create_form_from_preset(), delete_form(), form_stats(), FormCreate, FormFieldModel, FormSettingsModel, FormUpdate (+26 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (33): ai_generate_bid(), AIBidGenerateRequest, bid_stats(), BidCreate, BidItemModel, BidStatusUpdate, BidTemplateCreate, BidUpdate (+25 more)

### Community 23 - "Community 23"
Cohesion: 0.05
Nodes (14): auth_headers(), _b64url(), _make_jwt(), mock_supabase(), End-to-end tests for marketing infrastructure: campaigns, analytics, A/B tests,, Create a minimal JWT for testing (HS256)., Return JWT auth headers., Override tenant auth dependency for all requests. (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.05
Nodes (14): Tests for lead info extraction from chat messages.  These test the _extract_lead, A message that is just a capitalized name., Test extracting multiple fields from a single message., Test lead capture with partial information — name only, no email., Test the phone number regex matches international formats., Numbers with fewer than 7 digits should not be captured as phone., Test email parsing from chat messages., The extractor normalizes spaces around @. (+6 more)

### Community 25 - "Community 25"
Cohesion: 0.05
Nodes (31): create_document(), create_from_template(), create_template(), delete_document(), delete_template(), DocumentCreate, DocumentFromTemplate, get_document() (+23 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (29): AICampaignRequest, AIGenerateRequest, create_post(), delete_post(), generate_campaign_content(), generate_post_content(), get_analytics(), get_calendar() (+21 more)

### Community 27 - "Community 27"
Cohesion: 0.07
Nodes (35): _build_twiml_error(), _build_twiml_gather(), _build_twiml_goodbye(), _build_twiml_greeting(), CallListResponse, CallOut, CallStatsResponse, _find_tenant_by_phone() (+27 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (27): _make_auth_token(), Tests for authentication endpoints — signup, login, password reset, and checkout, Test the POST /api/v1/auth/register endpoint., Signing up with an existing email should return 409., New email should create tenant and return 200 with token., Test the POST /api/v1/auth/login endpoint., Login with non-existent email should return 401., Login with correct email but wrong password should return 401. (+19 more)

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (36): addMessage(), createWidget(), disableWidgetInput(), _esc(), fetchConfig(), fetchHistory(), formatBookingDate(), getSessionId() (+28 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (21): _make_token(), Tests for Client Portal endpoints — service records, portal links, and public po, Test POST /{tenant_id}/service-records., Test GET /{tenant_id}/service-records., Create a JWT signed with the test secret key., Test PUT /{tenant_id}/service-records/{record_id}., Empty update body should return 400., Test DELETE /{tenant_id}/service-records/{record_id}. (+13 more)

### Community 31 - "Community 31"
Cohesion: 0.08
Nodes (23): Tests for login flow, chat endpoint edge cases, and lead capture edge cases.  Us, Test the POST /api/v1/auth/login endpoint — 4 tests., Correct email/password returns 200 with token, tenant_id, etc., Correct email but wrong password returns 401., Login with email not in tenants or team_members returns 401., Request without email or password returns 422 validation error., Test POST /api/v1/widget/chat edge cases — 3 tests., Return table responses for a valid widget+tenant combo. (+15 more)

### Community 32 - "Community 32"
Cohesion: 0.1
Nodes (30): _auth_header(), _make_token(), Tests for the Local SEO Tools endpoints., Tests for GET /api/v1/seo/{tenant_id}., Tests for GET /api/v1/seo/{tenant_id}/keywords., Tests for GET /api/v1/seo/{tenant_id}/dashboard-widget., Configure db_mock.table() to return different data per table name., Unit tests for the _calculate_completeness helper. (+22 more)

### Community 33 - "Community 33"
Cohesion: 0.07
Nodes (20): AutomationConfigUpdate, _compute_twilio_signature(), _get_automation(), list_automations(), _lookup_tenant_by_twilio_number(), Automation management + Twilio missed-call / SMS-reply webhooks.  Production web, Find a tenant whose widget_configs row carries this Twilio number.      We store, Fetch a single automation by tenant + type. (+12 more)

### Community 34 - "Community 34"
Cohesion: 0.08
Nodes (33): client_login(), client_me(), client_register(), ClientLoginRequest, ClientRegisterRequest, _create_client_token(), create_service_record(), delete_service_record() (+25 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (21): _auth(), _make_token(), _mock_db(), Tests for previously untested messaging/webhook routers.  Covers: email_sequence, Submit with no body should return 422 validation error., test_create_note(), test_create_sequence(), test_facebook_status_no_integration() (+13 more)

### Community 36 - "Community 36"
Cohesion: 0.07
Nodes (25): ai_write_job_description(), AIJobWriteRequest, ApplicationStatusUpdate, create_job(), delete_job(), JobApplicationCreate, JobCreate, JobUpdate (+17 more)

### Community 37 - "Community 37"
Cohesion: 0.06
Nodes (13): Tests for industry-specific presets (pipeline stages, form presets)., Verify aftercare templates cover key industries., Verify rebook intervals for applicable industries., Verify business-profile dashboard defaults for key verticals., Verify pipeline presets cover all major industries., Verify form presets for all industries., Verify reminder extras cover key industries., TestAftercareTemplates (+5 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (24): OnlineStatusRequest, WidgetConfigResponse, AIFeedbackRequest, delete_ai_feedback(), generate_qr_code(), get_ai_feedback(), get_config(), _get_jwt_claims() (+16 more)

### Community 39 - "Community 39"
Cohesion: 0.07
Nodes (21): Exception, _OnboardingRecordingDb, _OnboardingRecordingQuery, Regression tests for backend wiring and analytics period handling., Small query double that records onboarding widget updates., Raised by tests to break the infinite automation loop., Preset defaults should not overwrite an already customized widget on re-run., Recurring invoices should run in the 30-minute automation tier. (+13 more)

### Community 40 - "Community 40"
Cohesion: 0.08
Nodes (20): Tests for Cycle 39 quick fixes: holiday hours, lead temperature, score factors., Test that score_lead sets lead_temperature based on score., Create a mock DB that returns lead and conversation data., Unit tests for _get_exception_for_date helper., Test that score_lead returns human-readable factor explanations., Test that generate_available_slots respects exception dates., Build a business_hours config dict., test_closed_holiday_returns_no_slots() (+12 more)

### Community 41 - "Community 41"
Cohesion: 0.09
Nodes (30): booking_page(), booking_submit(), BookingSubmitRequest, _build_booking_page_html(), build_reschedule_url(), _build_service_type_section(), _CancelBody, _fetch_widget_color() (+22 more)

### Community 42 - "Community 42"
Cohesion: 0.08
Nodes (7): control_center_client(), _make_jwt(), Tests for the Agent Control Center analytics payload., _StaticDb, _StaticQuery, test_control_center_aggregates_wins_risks_and_recovery_queue(), test_control_center_returns_empty_state_when_no_messages()

### Community 43 - "Community 43"
Cohesion: 0.07
Nodes (6): Tests for webhook delivery and retry logic., TestDailyLimit, TestDeliver, TestFireEvent, TestHMACSigning, TestSupportedEvents

### Community 44 - "Community 44"
Cohesion: 0.09
Nodes (21): ContentCreate, ContentUpdate, create_content(), delete_content(), get_content(), list_content(), _parse_platform_versions(), Content Studio endpoints — source content CRUD and AI repurposing. (+13 more)

### Community 45 - "Community 45"
Cohesion: 0.07
Nodes (20): create_stage(), delete_stage(), get_pipeline_analytics(), get_pipeline_board(), list_stages(), move_lead(), MoveleadRequest, Sales pipeline endpoints — stages, board view, analytics, and lead moves. (+12 more)

### Community 46 - "Community 46"
Cohesion: 0.1
Nodes (18): _make_token(), Tests for multi-tenant data isolation.  Verifies that Tenant A cannot access Ten, Tenant A cannot see Tenant B's conversations., Tenant A cannot see Tenant B's appointments., Tenant A cannot modify Tenant B's widget config., Tenant A cannot access Tenant B's dashboard., Tenant A cannot modify Tenant B's settings., Tenant A cannot access Tenant B's billing. (+10 more)

### Community 47 - "Community 47"
Cohesion: 0.09
Nodes (22): _make_jwt(), Tests for appointment endpoints — booking, listing, status updates, cancellation, Test POST /{tenant_id} — booking an appointment with valid data., POST with valid data returns 200 and appointment details., Test POST /{tenant_id} — booking in the past.      The endpoint does not explici, Booking with a past start time still processes (no 500)., Test GET /{tenant_id} — listing appointments., GET returns list of appointments for the tenant. (+14 more)

### Community 48 - "Community 48"
Cohesion: 0.08
Nodes (20): _make_jwt(), Tests for CORS configuration, rate limiting, and automation sequences.  Validate, Create a valid JWT token for test requests., Verify CORSMiddleware configuration in main.py.      The app uses allow_origins=, A request with any Origin header should get Access-Control-Allow-Origin back., With allow_origins=['*'], even unusual origins still get the wildcard header., OPTIONS preflight to /api/v1/widget/chat should return CORS headers., Verify that slowapi rate limiting is configured on key endpoints.      The app u (+12 more)

### Community 49 - "Community 49"
Cohesion: 0.09
Nodes (10): Tests for appointment booking — slot generation and overlap detection., Test double-booking prevention at the slot filtering level., Replicating the overlap check from booking.py., Test that appointments get linked to existing or new leads., Test appointment creation., Test slot generation logic., TestCreateAppointment, TestLeadLinkage (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.09
Nodes (19): _apply_filters(), create_smart_list(), _execute_smart_list_query(), export_smart_list(), get_smart_list_leads(), list_smart_lists(), Smart Lists — dynamic lead segments with filter-based queries and CSV export., Build and execute a leads query for a smart list's filters.      Args:         t (+11 more)

### Community 51 - "Community 51"
Cohesion: 0.1
Nodes (19): AIDraftRequest, create_review(), delete_review(), generate_ai_draft(), get_response_stats(), list_reviews(), Reviews management endpoints — Reputation Manager module., Return response history stats for a tenant's reviews.      Includes total/respon (+11 more)

### Community 52 - "Community 52"
Cohesion: 0.07
Nodes (26): ActionItem, AutomationRuleCreate, AutomationRuleUpdate, ConditionItem, create_automation_rule(), delete_automation_rule(), evaluate_automation_trigger(), EvaluateTriggerRequest (+18 more)

### Community 53 - "Community 53"
Cohesion: 0.09
Nodes (17): create_menu_item(), delete_menu_item(), import_menu_from_website(), list_categories(), list_menu_items(), MenuItemCreate, MenuItemUpdate, Menu management endpoints for restaurant tenants. (+9 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (25): build_oauth_flow(), _build_service(), create_calendar_event(), delete_calendar_event(), delete_integration(), exchange_code(), get_auth_url(), get_busy_times() (+17 more)

### Community 55 - "Community 55"
Cohesion: 0.1
Nodes (25): cancel_appointment(), create_appointment(), create_recurring_series(), generate_available_slots(), get_business_hours(), _get_exception_for_date(), link_appointment_to_lead(), list_appointments() (+17 more)

### Community 56 - "Community 56"
Cohesion: 0.1
Nodes (19): check_waitlist_for_date(), delete_waitlist_entry(), join_waitlist_public(), list_waitlist(), notify_waitlisted_customer(), Appointment waitlist — join, notify, manage waitlisted customers., List waitlist entries for a tenant, optionally filtered by status and date range, Waitlist summary stats. (+11 more)

### Community 57 - "Community 57"
Cohesion: 0.11
Nodes (19): create_flow(), create_from_template(), delete_flow(), flow_analytics(), FlowCreate, FlowUpdate, _get_cached(), list_flows() (+11 more)

### Community 58 - "Community 58"
Cohesion: 0.12
Nodes (25): assign_conversation(), AssignRequest, create_note(), delete_note(), _find_conversation(), get_presence(), list_notes(), NoteCreate (+17 more)

### Community 59 - "Community 59"
Cohesion: 0.11
Nodes (25): Backend Python Dependencies, Backend Workspace, Bug: 79% Hi Spam Messages, Bug: knowledge_base NULL for MTOptions, Bug: lead_captured Hardcoded False, Council: MTOptions Chatbot Audit, Council: Engineer Focus (Tester Conversion), Council: Hi Spam Problem (+17 more)

### Community 60 - "Community 60"
Cohesion: 0.14
Nodes (25): Academic Division (5 agents: anthropology, geography, history, narratology, psychology for world-building), The Agency: AI Specialist Framework, Agent Design Template (persona + operations: identity, mission, rules, deliverables, workflow, metrics), Agents Orchestrator (pipeline manager: PM -> Architecture -> Dev<->QA loops -> Integration), China Market Agents Cluster (Baidu SEO, Xiaohongshu, WeChat, Zhihu, Bilibili, Douyin, Kuaishou, Weibo, e-commerce, livestream, private domain), Content Docs (demo scripts, help articles, landing page copy), Design Division (8 agents: UI, UX research, UX architecture, brand, visual storytelling, whimsy, image prompts, inclusive visuals), Dev<->QA Continuous Loop (build -> test -> pass/fail -> retry, max 3 attempts) (+17 more)

### Community 61 - "Community 61"
Cohesion: 0.13
Nodes (23): check_contradictions(), check_duplicate_info(), check_memory_freshness(), check_stale_references(), generate_dream_report(), generate_summary_line(), get_recent_changed_files(), get_recent_git_log() (+15 more)

### Community 62 - "Community 62"
Cohesion: 0.08
Nodes (13): make_admin_request(), patch_admin_secret(), Tests for platform admin analytics and promotions endpoints., Patch the admin secret in all admin modules., Helper to make authenticated admin requests., No header and no fallback secret should return 401., TestAdminIndustryBreakdown, TestAdminMonthlyGrowth (+5 more)

### Community 63 - "Community 63"
Cohesion: 0.13
Nodes (23): _clean_business_name(), enrich_from_website(), _extract_domain(), _extract_phone_from_text(), gather_prospects(), _is_business_domain(), _is_valid_business_email(), main() (+15 more)

### Community 64 - "Community 64"
Cohesion: 0.12
Nodes (20): _allowed_tier_fields(), BusinessPagePublic, BusinessPageSettings, BusinessPageUpdate, _ensure_unique_slug(), get_business_page(), get_business_page_settings(), Business Page endpoints -- public hosted pages and dashboard management. (+12 more)

### Community 65 - "Community 65"
Cohesion: 0.1
Nodes (22): _decode_oauth_state(), _encode_oauth_state(), facebook_connection_status(), facebook_disconnect(), facebook_oauth_callback(), facebook_webhook_inbound(), facebook_webhook_verify(), FacebookStatusResponse (+14 more)

### Community 66 - "Community 66"
Cohesion: 0.17
Nodes (9): _make_jwt(), Tests for documents, item templates, and partial payments.  Uses the same mock p, _setup_table_mock(), TestDocumentCreate, TestDocumentDelete, TestDocumentList, TestDocumentSigning, TestItemTemplates (+1 more)

### Community 67 - "Community 67"
Cohesion: 0.2
Nodes (20): billing_portal(), create_checkout(), _handle_checkout_completed(), _handle_payment_failed(), _handle_subscription_deleted(), _handle_subscription_updated(), Stripe billing endpoints — checkout, webhooks, and customer portal., Determine plan from metadata, line items, or amount. (+12 more)

### Community 68 - "Community 68"
Cohesion: 0.1
Nodes (15): _decode_state(), _encode_state(), _get_current_tenant(), google_auth(), google_callback(), google_disconnect(), google_status(), Google Calendar OAuth integration endpoints. (+7 more)

### Community 69 - "Community 69"
Cohesion: 0.12
Nodes (15): create_snippet(), delete_snippet(), get_snippet(), list_snippets(), Snippets / Quick Replies — pre-written response templates for team conversations, Create a new snippet., AI suggests the best matching snippet based on conversation context., List snippets, sorted by usage_count descending (most-used first). (+7 more)

### Community 70 - "Community 70"
Cohesion: 0.13
Nodes (21): _calculate_live_revenue(), get_industry_breakdown(), get_monthly_growth(), get_plan_distribution(), get_platform_overview(), get_promoted_businesses(), get_revenue_trends(), get_weekly_growth() (+13 more)

### Community 71 - "Community 71"
Cohesion: 0.15
Nodes (15): _make_tenant(), _make_widget_config(), Tests for the widget chat API endpoints.  Tests the core widget functionality: c, Test widget config retrieval., Test widget chat endpoint., Test widget health endpoint., Create a FastAPI TestClient with mocked Supabase., _setup_table_mock() (+7 more)

### Community 72 - "Community 72"
Cohesion: 0.12
Nodes (20): _append_unsubscribe_footer(), build_branded_email_html(), _build_tracking_pixel(), build_unsubscribe_url(), _check_rate_limit(), _increment_send_count(), _make_unsub_sig(), Email sending service using Resend API with template rendering and rate limiting (+12 more)

### Community 73 - "Community 73"
Cohesion: 0.15
Nodes (20): connect_repurpose_outputs(), ConnectRequest, create_repurpose_job(), delete_repurpose_job(), get_repurpose_job(), list_repurpose_jobs(), Content Repurpose endpoints — create, list, edit, connect repurpose jobs., List repurpose jobs for a tenant. (+12 more)

### Community 74 - "Community 74"
Cohesion: 0.12
Nodes (7): _make_jwt(), Tests for automation extras: aftercare, rebook, birthday, lead sources., _setup_table_mock(), TestAftercareTemplates, TestLeadSourceAnalytics, TestRebookIntervals, TestReminderExtras

### Community 75 - "Community 75"
Cohesion: 0.13
Nodes (16): _make_jwt(), Tests for Google Calendar OAuth integration endpoints.  Validates the status che, GET /api/v1/integrations/google/status when no integration exists., Should return connected=false when no integration row exists., DELETE /api/v1/integrations/google when no integration exists., Should return gracefully even when no integration row exists., GET /api/v1/integrations/google/status when integration row exists., Should return connected=true with email when integration exists. (+8 more)

### Community 76 - "Community 76"
Cohesion: 0.15
Nodes (17): _auth_header(), _make_token(), Tests for Social Media Marketing and Campaign endpoints., Test AI content generation endpoints., Test marketing campaign CRUD., Test social media post create/list., test_create_campaign_invalid_type(), test_create_email_campaign() (+9 more)

### Community 77 - "Community 77"
Cohesion: 0.15
Nodes (11): _build_sample_payload(), create_webhook(), delete_webhook(), list_events(), list_webhooks(), recent_logs(), test_webhook(), toggle_webhook() (+3 more)

### Community 78 - "Community 78"
Cohesion: 0.13
Nodes (19): Blocked: Google Business Profile OAuth, Blocked Items, Blocked: Migrations 064-067, Blocked: requirements.txt Missing, Blocked: Real SERP Data, Blocked: Social Media OAuth, Feature: Content Repurposer, Integration: TikTok OAuth (+11 more)

### Community 79 - "Community 79"
Cohesion: 0.18
Nodes (8): _make_jwt(), Tests for service types, form presets, and birthday automation., Verify the birthday function can be imported., Verify the month-day matching works., _setup_table_mock(), TestBirthdayAutomation, TestFormPresets, TestServiceTypes

### Community 80 - "Community 80"
Cohesion: 0.12
Nodes (12): _automation_loop(), lifespan(), _process_scheduled_campaigns(), _process_scheduled_posts(), AgentNexLiFy — FastAPI application entry point., Run an automation function with a timeout. Logs results and exceptions., Background loop that runs automation tasks on a tiered schedule.      With multi, Mark marketing campaigns stuck in 'sending' for >30 minutes as 'failed'. (+4 more)

### Community 81 - "Community 81"
Cohesion: 0.15
Nodes (18): _decode_oauth_state(), disconnect_gbp(), _encode_oauth_state(), gbp_connection_status(), gbp_oauth_callback(), get_gbp_auth_url(), get_gbp_profile(), post_to_gbp() (+10 more)

### Community 82 - "Community 82"
Cohesion: 0.14
Nodes (19): Bug: Appointment double-booking race condition, Decision: Defense in Depth (App + DB constraints), Decision: HMAC-Signed Public URLs, Engineering State, Feature: Bulk Invoice Send, Feature: Appointment iCal Feed, Feature: Dashboard KPI Deltas, Feature: Lead CSV Export (+11 more)

### Community 83 - "Community 83"
Cohesion: 0.18
Nodes (17): check_backend_dangerous_imports(), check_code_smells_in_recent_commits(), check_env_safety(), check_frontend_syntax(), check_migration_consistency(), check_uncommitted_changes(), generate_health_report(), main() (+9 more)

### Community 84 - "Community 84"
Cohesion: 0.16
Nodes (15): _auth(), _make_token(), _pass_plan_check(), API-level tests for the content repurposer router.  Validates the full create ->, No-op replacement for _verify_plan., test_create_job(), test_create_job_free_plan_rejected(), test_create_job_invalid_source_type() (+7 more)

### Community 85 - "Community 85"
Cohesion: 0.15
Nodes (17): create_custom_field(), delete_custom_field(), FieldCreate, FieldUpdate, get_lead_custom_fields(), list_custom_fields(), Custom lead fields — per-tenant configurable attributes.  Lets businesses define, Update a custom field definition. (+9 more)

### Community 86 - "Community 86"
Cohesion: 0.14
Nodes (16): _coerce_money(), _extract_bid_request_from_response(), _extract_order_from_response(), _process_bid_request_from_chat(), _process_order_from_chat(), Widget booking-adjacent flows: restaurant order extraction and contractor bid re, Create an order record and send notifications to owner + customer., Extract structured order JSON from AI response, if present and valid. (+8 more)

### Community 87 - "Community 87"
Cohesion: 0.16
Nodes (16): create_scoring_factor(), delete_scoring_factor(), list_scoring_factors(), Lead scoring configuration — per-tenant customizable scoring weights., Create a custom scoring factor., Delete a custom scoring factor., Reset scoring factors to defaults (deletes all custom factors)., Seed default scoring factors for a tenant if none exist. (+8 more)

### Community 88 - "Community 88"
Cohesion: 0.16
Nodes (16): create_promotion(), delete_promotion(), expire_promotion(), get_promotion(), list_promotions(), PromotionCreate, PromotionUpdate, Admin Promotions CRUD — track and manage free/discounted business arrangements. (+8 more)

### Community 89 - "Community 89"
Cohesion: 0.17
Nodes (15): _compute_decay(), Lead scoring engine — rule-based 0-100 scoring with engagement, intent, recency,, Score based on how recently the lead was active. Max 20., Compute decay penalty for leads inactive > 7 days., Score a single lead and persist the result. Returns scoring details., Re-score all leads for a tenant. Returns summary., Fire-and-forget scoring wrapper for BackgroundTasks., Score based on contact info completeness and message volume. Max 40. (+7 more)

### Community 90 - "Community 90"
Cohesion: 0.23
Nodes (15): _get_cached(), _parse_dt(), _pct_change(), _period_to_days(), Revenue Analytics — unified financial reporting across invoices, pipeline, order, Daily revenue breakdown for charting., Top customers ranked by total revenue (invoices paid + orders)., Revenue breakdown by source type for pie/donut chart. (+7 more)

### Community 91 - "Community 91"
Cohesion: 0.17
Nodes (9): Tests for Stripe webhook signature verification and event handling., Test that different Stripe event types are routed to correct handlers., Test that the Stripe webhook endpoint validates signatures correctly., test_payment_failed_routed(), test_subscription_deleted_routed(), test_subscription_updated_routed(), test_unhandled_event_still_returns_ok(), TestStripeEventRouting (+1 more)

### Community 92 - "Community 92"
Cohesion: 0.18
Nodes (14): create_tag_definition(), delete_tag_definition(), _ensure_system_tags(), list_tag_definitions(), Tag definitions CRUD — manage AI conversation auto-categorization tags., Update a tag definition. System tags can only toggle is_enabled., Delete a custom tag definition. System tags cannot be deleted., Seed system tags for a tenant if they don't exist yet. (+6 more)

### Community 93 - "Community 93"
Cohesion: 0.18
Nodes (14): create_order(), get_order(), list_orders(), order_stats(), OrderCreate, OrderStatusUpdate, Order management endpoints for restaurant tenants., Create a new order (usually from the chat widget flow). (+6 more)

### Community 94 - "Community 94"
Cohesion: 0.28
Nodes (14): create_template(), delete_template(), list_templates(), preview_template(), Email templates API — reusable template library for automation sequences., List all email templates (starter + tenant custom)., Create a custom email template., Update a custom email template. (+6 more)

### Community 95 - "Community 95"
Cohesion: 0.14
Nodes (13): Tests for the content repurposer service., Only requested formats are returned., Plain text source returns content as-is with word count., HTML tags are stripped from text/podcast sources., Localhost and private URLs are rejected with ValueError., YouTube extraction mocks the transcript API and joins text entries., When no format filter is given, all 5 format keys are present., test_extract_source_text() (+5 more)

### Community 96 - "Community 96"
Cohesion: 0.26
Nodes (11): build_spreadsheet(), clean_email(), clean_phone(), extract_business_name(), main(), AgentNexLiFy Prospect List Builder Tries 3 approaches in order:   1. googlesearc, Visit a URL and extract phone/email via regex., Try to clean a page title into a business name. (+3 more)

### Community 97 - "Community 97"
Cohesion: 0.28
Nodes (12): _count_sentences(), EvalResult, EvalScenario, _evaluate_quality(), _extract_response_text(), _load_scenarios(), main(), _parse_args() (+4 more)

### Community 98 - "Community 98"
Cohesion: 0.19
Nodes (12): _cf_headers(), _execute_crawl(), get_crawl_status(), get_crawled_content(), _is_safe_url(), Website crawling service using Cloudflare Browser Rendering API.  Crawls a tenan, Call Cloudflare Browser Rendering /crawl endpoint and store results., Get the latest crawl status for a tenant. (+4 more)

### Community 99 - "Community 99"
Cohesion: 0.17
Nodes (11): mock_httpx_batch_response(), mock_httpx_response(), Tests for the embedding service., Mock a successful Voyage AI embedding response., Mock a successful batch embedding response., embed_text returns a 1024-dimension float list., embed_batch returns one vector per input text., embed_text truncates input longer than MAX_EMBED_CHARS. (+3 more)

### Community 100 - "Community 100"
Cohesion: 0.2
Nodes (4): ensure_directory(), relative_path(), skill_source_from_path(), write_json()

### Community 101 - "Community 101"
Cohesion: 0.35
Nodes (11): _clean_business_name(), enrich(), _extract_domain(), _extract_phone(), is_bad_email(), is_bad_name(), _is_business_domain(), _is_valid_email() (+3 more)

### Community 102 - "Community 102"
Cohesion: 0.27
Nodes (10): _check_daily_limit(), _deliver(), fire_event(), fire_event_background(), _increment_daily(), Webhook dispatcher — delivers event payloads to registered webhook URLs., POST payload to a single webhook URL. Log result. Retry up to 3 times with expon, Fire webhook event from a sync context by scheduling on the running event loop. (+2 more)

### Community 103 - "Community 103"
Cohesion: 0.18
Nodes (11): Bug: IDOR in auto_populate_kb, Bug: .get() or '' Operator Precedence, Bug: Widget CSS Overridden by Host Page, E2E Smoke Test 2026-04-05, Auto-KB Frontend + Share Results, MTOptions Chatbot Audit, Multi-Model Coding Agent (Aider + Qwen), Weekly Digest Email (+3 more)

### Community 104 - "Community 104"
Cohesion: 0.2
Nodes (1): Focused parser tests for local SEO AI JSON helpers.

### Community 105 - "Community 105"
Cohesion: 0.29
Nodes (9): _find_tenant_by_phone(), handle_inbound_sms(), handle_missed_call(), Twilio webhook endpoints — missed call text-back and inbound SMS handling.  When, Twilio messaging webhook — handles inbound SMS replies.      When a caller repli, Verify Twilio webhook signature (X-Twilio-Signature header)., Look up tenant by their configured notification_phone or Twilio number., Twilio voice webhook — triggered when a call goes unanswered.      Sends an auto (+1 more)

### Community 106 - "Community 106"
Cohesion: 0.24
Nodes (9): csat_stats(), list_csat_responses(), CSAT/NPS satisfaction survey endpoints.  Auto-sends satisfaction surveys after c, CSAT dashboard stats: avg rating, count, distribution, trend., List all CSAT responses., Public endpoint — customer submits their CSAT rating., submit_survey(), SurveySubmit (+1 more)

### Community 107 - "Community 107"
Cohesion: 0.39
Nodes (8): _duration(), _filter_entries(), _load_input_lines(), main(), _parse_args(), _parse_entries(), _percentile(), Summarize recent Railway HTTP latency from JSON log lines.  Examples:     python

### Community 108 - "Community 108"
Cohesion: 0.25
Nodes (1): Tests for centralized LLM runtime logging/safety behavior.

### Community 109 - "Community 109"
Cohesion: 0.36
Nodes (4): handleConnect(), handleDisconnect(), showMainView(), showSettingsView()

### Community 110 - "Community 110"
Cohesion: 0.36
Nodes (7): get_dashboard_business_profile(), get_widget_defaults(), humanize_business_type(), Business-type-aware defaults for widgets and dashboard personalization., Return widget defaults for the given business type., Return a dashboard-facing preset summary for a tenant., resolve_business_profile_key()

### Community 111 - "Community 111"
Cohesion: 0.25
Nodes (7): embed_batch(), embed_query(), embed_text(), Embedding service for knowledge base semantic search.  Uses Voyage AI (voyage-3-, Embed a single text string. Returns 512-dim vector., Embed multiple texts in one API call. Returns list of 512-dim vectors., Embed a search query. Uses input_type='query' for better retrieval.

### Community 112 - "Community 112"
Cohesion: 0.25
Nodes (7): format_textback_message(), looks_like_booking_request(), Twilio service — missed-call text-back and SMS utilities.  Production webhook UR, Send an SMS via the Twilio REST API., Interpolate {business_name} into the text-back template., Return True if the message contains booking-related keywords., send_sms()

### Community 113 - "Community 113"
Cohesion: 0.25
Nodes (7): crawl_content(), crawl_status(), Website crawl endpoints — start crawl, check status, get content., Start a website crawl for the tenant's website URL., Get the latest crawl status for a tenant., Get the extracted website content (for AI knowledge base preview)., trigger_crawl()

### Community 114 - "Community 114"
Cohesion: 0.32
Nodes (7): _handle_bounce(), Resend webhook endpoint for email event handling (bounces, complaints).  Handles, Mark the lead's email as bounced, scoped to the originating tenant.      Looks u, Verify Resend webhook signature using the svix headers.      Returns True when v, Handle Resend webhook events.      Supported events:     - email.bounced: marks, resend_webhook(), _verify_resend_signature()

### Community 115 - "Community 115"
Cohesion: 0.32
Nodes (7): get_wizard_stats(), log_wizard_event(), Wizard drop-off tracking — lightweight analytics for onboarding funnel., Log a wizard step event for drop-off tracking., Get wizard completion funnel stats., _verify_tenant(), WizardEvent

### Community 116 - "Community 116"
Cohesion: 0.29
Nodes (1): Focused parser-seam tests for AI-generated route outputs.

### Community 117 - "Community 117"
Cohesion: 0.29
Nodes (1): Focused tests for content repurposer JSON parsing / repair helpers.

### Community 118 - "Community 118"
Cohesion: 0.43
Nodes (6): check_sms_rate_limit(), get_sms_usage(), increment_sms_count(), _maybe_reset(), SMS rate limiting — in-memory daily tracking per tenant., Return True if tenant is within daily SMS limit.

### Community 119 - "Community 119"
Cohesion: 0.29
Nodes (0):

### Community 120 - "Community 120"
Cohesion: 0.29
Nodes (6): Phase 4: Code Quality, Phase 1: Critical Fixes, Phase 5: Omnichannel Foundation, Phase 2: Performance, Phase 3: Quick-Win Features, Platform Improvements Design Spec

### Community 121 - "Community 121"
Cohesion: 0.33
Nodes (5): get_business_context(), Shared FastAPI dependencies for AgentNexLiFy backend.  Contains utilities that w, Verify the JWT claims match the requested tenant. Raises 403 if not., Fetch business name and type from the tenants table for AI context.      Returns, verify_tenant()

### Community 122 - "Community 122"
Cohesion: 0.4
Nodes (4): _ensure_initialized(), get_or_create_customer(), Stripe client singleton and billing helpers., Find existing Stripe customer by tenant metadata, or create one.

### Community 123 - "Community 123"
Cohesion: 0.4
Nodes (5): _handle_invoice_payment(), Stripe webhook endpoint at /api/v1/webhooks/stripe.  Delegates to the same handl, Handle Stripe webhook events via /api/v1/webhooks/stripe., Handle payment for an AgentNexLiFy invoice (via Stripe Payment Link).      Updat, stripe_webhook()

### Community 124 - "Community 124"
Cohesion: 0.47
Nodes (6): Skill: caveman, Skill: diagram-it, Skill: nano-this, Skill Schema Definition, Skill: ver-it, Skill: vis-it

### Community 125 - "Community 125"
Cohesion: 0.33
Nodes (6): Council Advisor: The Contrarian, Council Advisor: The Executor, Council Advisor: The Expansionist, Council Advisor: First Principles Thinker, Council Advisor: The Outsider, LLM Council Skill

### Community 126 - "Community 126"
Cohesion: 0.4
Nodes (1): Tests for selective retry adoption in non-latency-critical AI paths.

### Community 127 - "Community 127"
Cohesion: 0.4
Nodes (1): Targeted tests for centralized onboarding AI paths and parser behavior.

### Community 128 - "Community 128"
Cohesion: 0.4
Nodes (5): Analytics Dashboard Upgrade, Chat Flow Builder, Response Time Tracking, Snippets & Quick Replies, Daily Log 2026-03-15

### Community 129 - "Community 129"
Cohesion: 0.6
Nodes (5): Coding Agents Setup, Tool: Aider, Tool: Claude Code, Tool: Ollama local models, Tool: Qwen 3.6 Plus

### Community 130 - "Community 130"
Cohesion: 0.67
Nodes (3): main(), _print_summary(), One-off test: simulate and send the weekly digest email for MTOptions tenant.  U

### Community 131 - "Community 131"
Cohesion: 0.5
Nodes (3): log_activity(), Activity logging service — fire-and-forget, never raises., Insert a row into activity_log. Silently swallows errors.

### Community 132 - "Community 132"
Cohesion: 0.5
Nodes (3): Retry utility for transient external service failures (Anthropic, Resend, Twilio, Call fn() with exponential backoff retries on transient errors.      Retries on:, with_retry()

### Community 133 - "Community 133"
Cohesion: 0.5
Nodes (3): ingest_channel_message(), Omnichannel message ingestion layer.  Schema notes (confirmed by live schema and, Normalize and store an inbound channel message (legacy path).      Args:

### Community 134 - "Community 134"
Cohesion: 0.5
Nodes (3): list_webhook_deliveries(), Webhook delivery log endpoint — shows recent deliveries per webhook., Return recent webhook_logs for a specific webhook.

### Community 135 - "Community 135"
Cohesion: 0.5
Nodes (4): Anti-Desperation Error Handling, Compound Engineering Pipeline, Self-Improvement Loop, 3-Layer Workspace Routing

### Community 136 - "Community 136"
Cohesion: 0.67
Nodes (1): Seed the MTOptions Welcome Sequence in email_sequences.  Looks up the MTOptions

### Community 137 - "Community 137"
Cohesion: 0.67
Nodes (0):

### Community 138 - "Community 138"
Cohesion: 0.67
Nodes (2): BaseSettings, Settings

### Community 139 - "Community 139"
Cohesion: 0.67
Nodes (2): _get_real_client_ip(), Extract the real client IP behind Railway's proxy.      Railway (and most revers

### Community 140 - "Community 140"
Cohesion: 1.0
Nodes (2): getPresetWidgetDefaults(), resolvePresetKey()

### Community 141 - "Community 141"
Cohesion: 1.0
Nodes (0):

### Community 142 - "Community 142"
Cohesion: 1.0
Nodes (2): Issue: Kairos Reports UNHEALTHY (future import), Kairos Health 2026-04-04

### Community 143 - "Community 143"
Cohesion: 1.0
Nodes (2): Deterministic-First Rule, RTK Token Optimization

### Community 144 - "Community 144"
Cohesion: 1.0
Nodes (2): Automation Sequences Table, Email Sequences Table

### Community 145 - "Community 145"
Cohesion: 1.0
Nodes (2): Test Matrix, Test Results

### Community 146 - "Community 146"
Cohesion: 1.0
Nodes (0):

### Community 147 - "Community 147"
Cohesion: 1.0
Nodes (0):

### Community 148 - "Community 148"
Cohesion: 1.0
Nodes (1): Message at max_length (10000 chars) should be accepted.

### Community 149 - "Community 149"
Cohesion: 1.0
Nodes (1): Valid API key should return widget config.

### Community 150 - "Community 150"
Cohesion: 1.0
Nodes (1): When a profile already exists, it should update (not insert).

### Community 151 - "Community 151"
Cohesion: 1.0
Nodes (1): A date marked closed in exceptions should return zero slots.

### Community 152 - "Community 152"
Cohesion: 1.0
Nodes (1): A date with open/close override should use those hours instead of normal day hou

### Community 153 - "Community 153"
Cohesion: 1.0
Nodes (1): Days not in exceptions should use normal hours.

### Community 154 - "Community 154"
Cohesion: 1.0
Nodes (1): Lead with email + phone + pricing + availability + recent = hot.

### Community 155 - "Community 155"
Cohesion: 1.0
Nodes (1): Lead with email + name + some messages = warm.

### Community 156 - "Community 156"
Cohesion: 1.0
Nodes (1): Lead with minimal info = cold.

### Community 157 - "Community 157"
Cohesion: 1.0
Nodes (1): Factors list includes email and phone when present.

### Community 158 - "Community 158"
Cohesion: 1.0
Nodes (1): Factors list includes intent keywords when user asked about pricing.

### Community 159 - "Community 159"
Cohesion: 1.0
Nodes (1): Result dict always has factors and temperature keys.

### Community 160 - "Community 160"
Cohesion: 1.0
Nodes (1): Free plan should not access repurposer.

### Community 161 - "Community 161"
Cohesion: 1.0
Nodes (1): One due execution → execute_step called once → returns 1.

### Community 162 - "Community 162"
Cohesion: 1.0
Nodes (1): Empty result from DB → returns 0 without calling execute_step.

### Community 163 - "Community 163"
Cohesion: 1.0
Nodes (1): Three due executions → execute_step called three times → returns 3.

### Community 164 - "Community 164"
Cohesion: 1.0
Nodes (1): If execute_step raises on first execution, the second one still runs.

### Community 165 - "Community 165"
Cohesion: 1.0
Nodes (1): Matching sequence + first step → creates execution row → returns 1.

### Community 166 - "Community 166"
Cohesion: 1.0
Nodes (1): Sequence targets 'closed' but new_stage='contacted' → no enrollment → 0.

### Community 167 - "Community 167"
Cohesion: 1.0
Nodes (1): No sequences for this tenant+trigger → returns 0 immediately.

### Community 168 - "Community 168"
Cohesion: 1.0
Nodes (1): DB insert raises (UNIQUE constraint) → caught, enrollment count stays 0.

### Community 169 - "Community 169"
Cohesion: 1.0
Nodes (1): Invoice past due_date → status updated to 'overdue' + email reminder sent.

### Community 170 - "Community 170"
Cohesion: 1.0
Nodes (1): Invoice due tomorrow → email reminder sent with 'tomorrow' in subject.

### Community 171 - "Community 171"
Cohesion: 1.0
Nodes (1): activity_log dedup hit for today → email NOT sent → returns 0.

### Community 172 - "Community 172"
Cohesion: 1.0
Nodes (1): Invoice with lead_id=None → skipped early without crash or email.

### Community 173 - "Community 173"
Cohesion: 1.0
Nodes (1): Non-Monday weekday → returns 0, no email sent.          Note: get_supabase IS ca

### Community 174 - "Community 174"
Cohesion: 1.0
Nodes (1): Monday + paid tenant + no dedup hit → email sent → returns 1.

### Community 175 - "Community 175"
Cohesion: 1.0
Nodes (1): Monday but dedup hit in activity_log → returns 0, no email sent.

### Community 176 - "Community 176"
Cohesion: 1.0
Nodes (1): Free-plan tenants are excluded by .neq('plan', 'free') at the DB level.

### Community 177 - "Community 177"
Cohesion: 1.0
Nodes (1): If another worker advances the parent first, no duplicate child invoice is creat

### Community 178 - "Community 178"
Cohesion: 1.0
Nodes (1): If child invoice creation fails after the claim, next_invoice_date is restored.

### Community 179 - "Community 179"
Cohesion: 1.0
Nodes (1): Lead created 25h ago with no conversation → trigger_sequence called.

### Community 180 - "Community 180"
Cohesion: 1.0
Nodes (1): Lead has a message within the last 24h → skip, trigger_sequence NOT called.

### Community 181 - "Community 181"
Cohesion: 1.0
Nodes (1): Lead already has an in_progress execution for a no_response_24h sequence.

### Community 182 - "Community 182"
Cohesion: 1.0
Nodes (1): No 'new' leads older than 24h → returns 0, trigger_sequence not called.

### Community 183 - "Community 183"
Cohesion: 1.0
Nodes (1): Public endpoint — no auth needed, uses api_key.

### Community 184 - "Community 184"
Cohesion: 1.0
Nodes (1): Public endpoint — token format is tenant_id:session_id.

### Community 185 - "Community 185"
Cohesion: 1.0
Nodes (1): Slots overlapping with existing appointments should be excluded.

### Community 186 - "Community 186"
Cohesion: 1.0
Nodes (1): Buffer minutes should increase the step between slots.

### Community 187 - "Community 187"
Cohesion: 1.0
Nodes (1): When no lead exists for the email, creates a new one with client_id.

### Community 188 - "Community 188"
Cohesion: 1.0
Nodes (1): Twilio webhooks require valid signature — unsigned requests fail.

### Community 189 - "Community 189"
Cohesion: 1.0
Nodes (0):

### Community 190 - "Community 190"
Cohesion: 1.0
Nodes (0):

### Community 191 - "Community 191"
Cohesion: 1.0
Nodes (1): Competitor: Phonely (YC S24)

### Community 192 - "Community 192"
Cohesion: 1.0
Nodes (1): Competitor: Toma (a16z + YC)

### Community 193 - "Community 193"
Cohesion: 1.0
Nodes (1): Competitor: Oscar Chat

### Community 194 - "Community 194"
Cohesion: 1.0
Nodes (1): Today Task List 2026-03-12

### Community 195 - "Community 195"
Cohesion: 1.0
Nodes (1): Lead Merge

### Community 196 - "Community 196"
Cohesion: 1.0
Nodes (1): Job Listings in Widget

### Community 197 - "Community 197"
Cohesion: 1.0
Nodes (1): Auto-Publish Scheduled Posts/Campaigns

### Community 198 - "Community 198"
Cohesion: 1.0
Nodes (1): Agent Delegation System

### Community 199 - "Community 199"
Cohesion: 1.0
Nodes (1): LLM Council Decision System

### Community 200 - "Community 200"
Cohesion: 1.0
Nodes (1): Chat Messages Table

### Community 201 - "Community 201"
Cohesion: 1.0
Nodes (1): Invoices Table

### Community 202 - "Community 202"
Cohesion: 1.0
Nodes (1): Marketing Campaigns Table

### Community 203 - "Community 203"
Cohesion: 1.0
Nodes (1): Documents & E-Signatures Table

### Community 204 - "Community 204"
Cohesion: 1.0
Nodes (1): Competitive Intelligence

### Community 205 - "Community 205"
Cohesion: 1.0
Nodes (1): AI Review Responder Chrome Extension

### Community 206 - "Community 206"
Cohesion: 1.0
Nodes (1): API Key Prefix anx_

### Community 207 - "Community 207"
Cohesion: 1.0
Nodes (1): httpx==0.28.1

### Community 208 - "Community 208"
Cohesion: 1.0
Nodes (1): mcp>=1.0.0

### Community 209 - "Community 209"
Cohesion: 1.0
Nodes (1): GitHub Actions CI/CD

### Community 210 - "Community 210"
Cohesion: 1.0
Nodes (1): Migration 024 - Appointments updated_at

### Community 211 - "Community 211"
Cohesion: 1.0
Nodes (1): Migration 042 - Contractor Bid Manager

### Community 212 - "Community 212"
Cohesion: 1.0
Nodes (1): Migration 050 - Social Media Marketing

### Community 213 - "Community 213"
Cohesion: 1.0
Nodes (1): Migration 052 - Sales Pipeline

### Community 214 - "Community 214"
Cohesion: 1.0
Nodes (1): Migration 054 - Form Builder

### Community 215 - "Community 215"
Cohesion: 1.0
Nodes (1): Migration 061 - Documents E-Signatures

### Community 216 - "Community 216"
Cohesion: 1.0
Nodes (1): Migration 069 - Lead Email Bounced

### Community 217 - "Community 217"
Cohesion: 1.0
Nodes (1): Session 2026-03-24

### Community 218 - "Community 218"
Cohesion: 1.0
Nodes (1): Knowledge Base PENDING

## Knowledge Gaps
- **1158 isolated node(s):** `One-off test: simulate and send the weekly digest email for MTOptions tenant.  U`, `Seed the MTOptions Welcome Sequence in email_sequences.  Looks up the MTOptions`, `Read a file, return empty string on failure.`, `Read all .md files from the memory directory.`, `Read key dev-knowledge files.` (+1153 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 141`** (2 nodes): `database.py`, `get_supabase()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 142`** (2 nodes): `Issue: Kairos Reports UNHEALTHY (future import)`, `Kairos Health 2026-04-04`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 143`** (2 nodes): `Deterministic-First Rule`, `RTK Token Optimization`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 144`** (2 nodes): `Automation Sequences Table`, `Email Sequences Table`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 145`** (2 nodes): `Test Matrix`, `Test Results`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 146`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 147`** (1 nodes): `demoConfig.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 148`** (1 nodes): `Message at max_length (10000 chars) should be accepted.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 149`** (1 nodes): `Valid API key should return widget config.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 150`** (1 nodes): `When a profile already exists, it should update (not insert).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 151`** (1 nodes): `A date marked closed in exceptions should return zero slots.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 152`** (1 nodes): `A date with open/close override should use those hours instead of normal day hou`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 153`** (1 nodes): `Days not in exceptions should use normal hours.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 154`** (1 nodes): `Lead with email + phone + pricing + availability + recent = hot.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 155`** (1 nodes): `Lead with email + name + some messages = warm.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 156`** (1 nodes): `Lead with minimal info = cold.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 157`** (1 nodes): `Factors list includes email and phone when present.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 158`** (1 nodes): `Factors list includes intent keywords when user asked about pricing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 159`** (1 nodes): `Result dict always has factors and temperature keys.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 160`** (1 nodes): `Free plan should not access repurposer.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 161`** (1 nodes): `One due execution → execute_step called once → returns 1.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 162`** (1 nodes): `Empty result from DB → returns 0 without calling execute_step.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 163`** (1 nodes): `Three due executions → execute_step called three times → returns 3.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 164`** (1 nodes): `If execute_step raises on first execution, the second one still runs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 165`** (1 nodes): `Matching sequence + first step → creates execution row → returns 1.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 166`** (1 nodes): `Sequence targets 'closed' but new_stage='contacted' → no enrollment → 0.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 167`** (1 nodes): `No sequences for this tenant+trigger → returns 0 immediately.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 168`** (1 nodes): `DB insert raises (UNIQUE constraint) → caught, enrollment count stays 0.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 169`** (1 nodes): `Invoice past due_date → status updated to 'overdue' + email reminder sent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 170`** (1 nodes): `Invoice due tomorrow → email reminder sent with 'tomorrow' in subject.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 171`** (1 nodes): `activity_log dedup hit for today → email NOT sent → returns 0.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 172`** (1 nodes): `Invoice with lead_id=None → skipped early without crash or email.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 173`** (1 nodes): `Non-Monday weekday → returns 0, no email sent.          Note: get_supabase IS ca`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 174`** (1 nodes): `Monday + paid tenant + no dedup hit → email sent → returns 1.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 175`** (1 nodes): `Monday but dedup hit in activity_log → returns 0, no email sent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 176`** (1 nodes): `Free-plan tenants are excluded by .neq('plan', 'free') at the DB level.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 177`** (1 nodes): `If another worker advances the parent first, no duplicate child invoice is creat`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 178`** (1 nodes): `If child invoice creation fails after the claim, next_invoice_date is restored.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 179`** (1 nodes): `Lead created 25h ago with no conversation → trigger_sequence called.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 180`** (1 nodes): `Lead has a message within the last 24h → skip, trigger_sequence NOT called.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 181`** (1 nodes): `Lead already has an in_progress execution for a no_response_24h sequence.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 182`** (1 nodes): `No 'new' leads older than 24h → returns 0, trigger_sequence not called.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 183`** (1 nodes): `Public endpoint — no auth needed, uses api_key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 184`** (1 nodes): `Public endpoint — token format is tenant_id:session_id.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 185`** (1 nodes): `Slots overlapping with existing appointments should be excluded.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 186`** (1 nodes): `Buffer minutes should increase the step between slots.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 187`** (1 nodes): `When no lead exists for the email, creates a new one with client_id.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 188`** (1 nodes): `Twilio webhooks require valid signature — unsigned requests fail.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 189`** (1 nodes): `background.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 190`** (1 nodes): `index.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 191`** (1 nodes): `Competitor: Phonely (YC S24)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 192`** (1 nodes): `Competitor: Toma (a16z + YC)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 193`** (1 nodes): `Competitor: Oscar Chat`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 194`** (1 nodes): `Today Task List 2026-03-12`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 195`** (1 nodes): `Lead Merge`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 196`** (1 nodes): `Job Listings in Widget`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 197`** (1 nodes): `Auto-Publish Scheduled Posts/Campaigns`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 198`** (1 nodes): `Agent Delegation System`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 199`** (1 nodes): `LLM Council Decision System`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 200`** (1 nodes): `Chat Messages Table`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 201`** (1 nodes): `Invoices Table`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 202`** (1 nodes): `Marketing Campaigns Table`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 203`** (1 nodes): `Documents & E-Signatures Table`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 204`** (1 nodes): `Competitive Intelligence`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 205`** (1 nodes): `AI Review Responder Chrome Extension`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 206`** (1 nodes): `API Key Prefix anx_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 207`** (1 nodes): `httpx==0.28.1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 208`** (1 nodes): `mcp>=1.0.0`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 209`** (1 nodes): `GitHub Actions CI/CD`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 210`** (1 nodes): `Migration 024 - Appointments updated_at`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 211`** (1 nodes): `Migration 042 - Contractor Bid Manager`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 212`** (1 nodes): `Migration 050 - Social Media Marketing`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 213`** (1 nodes): `Migration 052 - Sales Pipeline`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 214`** (1 nodes): `Migration 054 - Form Builder`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 215`** (1 nodes): `Migration 061 - Documents E-Signatures`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 216`** (1 nodes): `Migration 069 - Lead Email Bounced`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 217`** (1 nodes): `Session 2026-03-24`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 218`** (1 nodes): `Knowledge Base PENDING`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentControlCenterResponse` connect `Marketing Tests` to `Auth & Session Management`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **Why does `FacebookStatusResponse` connect `Community 65` to `Auth & Session Management`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `MockSupabaseTable` (e.g. with `.table()` and `TestVoiceIncoming`) actually correct?**
  _`MockSupabaseTable` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `MockSupabaseClient` (e.g. with `mock_supabase()` and `TestVoiceIncoming`) actually correct?**
  _`MockSupabaseClient` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `MockSupabaseResponse` (e.g. with `.execute()` and `TestVoiceIncoming`) actually correct?**
  _`MockSupabaseResponse` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `LeadScoreResponse` (e.g. with `LeadCreateRequest` and `QuickEmailRequest`) actually correct?**
  _`LeadScoreResponse` has 27 INFERRED edges - model-reasoned connections that need verification._
- **What connects `One-off test: simulate and send the weekly digest email for MTOptions tenant.  U`, `Seed the MTOptions Welcome Sequence in email_sequences.  Looks up the MTOptions`, `Read a file, return empty string on failure.` to the rest of the system?**
  _1158 weakly-connected nodes found - possible documentation gaps or missing edges._
