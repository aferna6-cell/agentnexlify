# Graph Report - .  (2026-04-07)

## Corpus Check
- Large corpus: 596 files · ~741,330 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 4137 nodes · 6010 edges · 298 communities detected
- Extraction: 67% EXTRACTED · 32% INFERRED · 0% AMBIGUOUS · INFERRED: 1897 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `MockSupabaseTable` - 59 edges
2. `MockSupabaseClient` - 43 edges
3. `MockSupabaseResponse` - 41 edges
4. `The Agency — AI Specialist Agent Collection` - 38 edges
5. `LeadScoreResponse` - 29 edges
6. `ScoreAllResponse` - 29 edges
7. `LeadUpdateRequest` - 29 edges
8. `_mock_db()` - 23 edges
9. `AvailabilityConfigRequest` - 23 edges
10. `AvailabilityConfigResponse` - 23 edges

## Surprising Connections (you probably didn't know these)
- `LLM Council (5 AI Advisor Decision Framework)` --semantically_similar_to--> `Compound Engineering 5-Agent Pipeline`  [INFERRED] [semantically similar]
  GEMINI.md → CLAUDE.md
- `Dashboard notifications center — aggregates recent activity into a single feed.` --uses--> `ClientRow`  [INFERRED]
  /home/aidan/agentnexlify/backend/routers/notifications.py → backend/models/schemas.py
- `Send notification to the real estate agent via email (and SMS if configured).` --uses--> `ClientRow`  [INFERRED]
  _archive/backend/services/notifications.py → backend/models/schemas.py
- `Webhook management endpoints — CRUD for webhook configurations and delivery logs` --uses--> `ClientRow`  [INFERRED]
  /home/aidan/agentnexlify/backend/routers/webhooks.py → backend/models/schemas.py
- `Handle incoming SMS via Twilio webhook.      Maps the receiving phone number to` --uses--> `ClientRow`  [INFERRED]
  _archive/backend/routers/webhooks.py → backend/models/schemas.py

## Hyperedges (group relationships)
- **Agent Delegation Pipeline: schema-guardian → backend-dev + frontend-dev → qa-tester → devops** — claude_schema_guardian_agent, claude_backend_dev_agent, claude_frontend_dev_agent, claude_qa_tester_agent, claude_devops_agent [EXTRACTED 1.00]
- **Three-Layer AI Development System: Brain+Skills, Slash Commands, Automated Enforcement** — agents_claude_skills, aidev_pre_commit_hook, aidev_github_actions [EXTRACTED 0.95]
- **Schema Critical Rules Triangle: client_id, no __future__ annotations, RLS** — claude_client_id_rule, claude_no_future_annotations, claude_rls_policies [EXTRACTED 0.90]
- **Roblox Studio Agent Group** —  [1.0]
- **Unreal Engine Agent Group** —  [1.0]
- **Godot Agent Group** —  [1.0]
- **Unity Agent Group** —  [1.0]
- **Sales Agent Group** —  [1.0]
- **Server-Authoritative Multiplayer Pattern** —  [1.0]
- **Startup MVP Workflow Agent Team** —  [1.0]
- **XR/Spatial Computing Agent Stack** —  [INFERRED]
- **Security & Detection Agent Cluster** —  [INFERRED]
- **Onboarding Email Sequence** —  [INFERRED]
- **Demo & Sales Content Assets** —  [INFERRED]

## Communities

### Community 0 - "Core App & Chat Engine"
Cohesion: 0.02
Nodes (224): ChatMessage, ChatRequest, AgentNexLiFy Demo — Chat API Backend (FastAPI + Anthropic)., billing_cancel(), billing_change_plan(), billing_checkout(), billing_portal(), _compute_trial_status() (+216 more)

### Community 1 - "Marketing Campaigns"
Cohesion: 0.02
Nodes (27): ApiError, handleUnauthorized(), request(), create_snippet(), delete_snippet(), get_snippet(), list_snippets(), Snippets / Quick Replies — pre-written response templates for team conversations (+19 more)

### Community 2 - "Test Infrastructure"
Cohesion: 0.04
Nodes (65): _clear_widget_cache(), mock_settings(), mock_supabase(), MockSupabaseClient, MockSupabaseResponse, MockSupabaseTable, Shared test fixtures for AgentNexLiFy tests., Provide a mock Supabase client and patch get_supabase. (+57 more)

### Community 3 - "Agency Agents & Strategy"
Cohesion: 0.03
Nodes (88): ADR-003: Multi-Tenant Agency Architecture, ADR-001: SSE Streaming for Widget, ADR-004: Stripe Checkout Migration, ADR-002: Vapi Voice Integration, Answer Engine Optimization (AEO) / Generative Engine Optimization (GEO), The Agency Contributing Guide, The Agency Contributing Guide (Chinese), Agent: AI Citation Strategist (AEO/GEO) (+80 more)

### Community 4 - "Auto-Improver & Code Quality"
Cohesion: 0.04
Nodes (21): AutonomousImprover, main(), EvaluationEngine, main(), _split_csv(), main(), PatternExtractor, main() (+13 more)

### Community 5 - "Automation Engine"
Cohesion: 0.04
Nodes (71): _advance_execution(), check_appointment_triggers(), check_form_submission_triggers(), check_lead_captured_triggers(), check_new_reviews(), check_no_response_leads(), check_tag_triggers(), _evaluate_conditions() (+63 more)

### Community 6 - "Lead Management"
Cohesion: 0.06
Nodes (49): assign_lead(), AssignLeadRequest, bulk_update_leads(), BulkUpdateRequest, create_lead(), debug_lead_capture(), export_leads_csv(), find_duplicate_leads() (+41 more)

### Community 7 - "Appointment Booking"
Cohesion: 0.13
Nodes (48): book_appointment(), create_service_type(), dashboard_book_appointment(), _DashboardBookBody, delete_appointment(), delete_service_type(), get_appointments(), get_availability() (+40 more)

### Community 8 - "Automation Tests"
Cohesion: 0.04
Nodes (30): _chain_table(), _make_db_mock(), Tests for the automation engine service.  Covers: process_pending_steps, send_in, Tests for trigger_sequence()., Tests for send_invoice_payment_reminders()., Return a (db, table) pair where every chained Supabase call returns the     same, Tests for send_weekly_intelligence_briefs().      The function imports `settings, Tests for process_pending_steps(). (+22 more)

### Community 9 - "Widget Chat Helpers"
Cohesion: 0.05
Nodes (51): _build_conversation_summary(), _build_flow_instructions(), _build_intent_window(), _build_system_prompt(), _capture_leads_from_session(), _categorize_conversation(), _compact_messages_for_llm(), _extract_action_items() (+43 more)

### Community 10 - "Local SEO & GEO"
Cohesion: 0.06
Nodes (51): _analyze_keywords_ai(), analyze_seo_profile(), _calculate_completeness(), calculate_geo_score(), CompetitorRequest, DashboardWidgetResponse, _generate_keywords(), GEOScoreRequest (+43 more)

### Community 11 - "Analytics Dashboard"
Cohesion: 0.07
Nodes (38): analytics_health(), _build_control_center_recommendations(), _clamp_score(), _date_range(), _first_response_seconds(), get_agent_control_center(), get_ai_insights(), _get_cached() (+30 more)

### Community 12 - "CRUD Route Tests"
Cohesion: 0.08
Nodes (37): _auth(), _make_token(), _mock_db(), Tests for previously untested CRUD routers.  Covers: snippets, tag_definitions,, test_create_automation(), test_create_bid(), test_create_field(), test_create_scoring_factor() (+29 more)

### Community 13 - "Email Sequences"
Cohesion: 0.05
Nodes (37): add_step(), create_sequence(), delete_sequence(), delete_step(), _enroll_lead(), enroll_lead_in_sequences(), EnrollRequest, get_sequence() (+29 more)

### Community 14 - "Business Page Tests"
Cohesion: 0.05
Nodes (20): http_client(), Tests for business page endpoints — public page + dashboard settings., Test the data mapping for the public business page., Configure db_mock.table() to return different data per table name., Create a FastAPI TestClient with mocked Supabase for endpoint tests., Integration tests for GET /biz/{slug} endpoint., GET /biz/{slug} with a valid, enabled slug returns 200 with page data., GET /biz/{slug} with a slug that does not exist returns 404. (+12 more)

### Community 15 - "Forms & Surveys"
Cohesion: 0.05
Nodes (34): create_form(), create_form_from_preset(), delete_form(), form_stats(), FormCreate, FormFieldModel, FormSettingsModel, FormUpdate (+26 more)

### Community 16 - "Python Linting Tools"
Cohesion: 0.09
Nodes (24): call_name(), collect_mock_symbols(), expression_root_name(), files_to_scan(), Finding, FunctionAssertionAnalyzer, InteractionExpressionVisitor, is_assertion_call_interaction_only() (+16 more)

### Community 17 - "Bids & Estimates"
Cohesion: 0.06
Nodes (33): ai_generate_bid(), AIBidGenerateRequest, bid_stats(), BidCreate, BidItemModel, BidStatusUpdate, BidTemplateCreate, BidUpdate (+25 more)

### Community 18 - "Marketing Tests"
Cohesion: 0.05
Nodes (14): auth_headers(), _b64url(), _make_jwt(), mock_supabase(), End-to-end tests for marketing infrastructure: campaigns, analytics, A/B tests,, Create a minimal JWT for testing (HS256)., Return JWT auth headers., Override tenant auth dependency for all requests. (+6 more)

### Community 19 - "Lead Extraction Tests"
Cohesion: 0.05
Nodes (14): Tests for lead info extraction from chat messages.  These test the _extract_lead, A message that is just a capitalized name., Test extracting multiple fields from a single message., Test lead capture with partial information — name only, no email., Test the phone number regex matches international formats., Numbers with fewer than 7 digits should not be captured as phone., Test email parsing from chat messages., The extractor normalizes spaces around @. (+6 more)

### Community 20 - "AI Architecture & DevOps"
Cohesion: 0.05
Nodes (41): Widget Post-Processing AI (tag extraction, categorization), Widget Chat Runtime (widget_chat.py), Schema Mismatch Risk: tenant_id vs client_id in Multiple Files, GitHub Actions (daily health, PR validation), Pre-Commit Hook (secrets/imports check), Pre-Push Hook (build/schema check), Schema Guard Skill, v0.1.0 Release (pre-production beta, 94 migrations, 305+ tests) (+33 more)

### Community 21 - "Documents & E-Signatures"
Cohesion: 0.05
Nodes (31): create_document(), create_from_template(), create_template(), delete_document(), delete_template(), DocumentCreate, DocumentFromTemplate, get_document() (+23 more)

### Community 22 - "Embeddable Widget JS"
Cohesion: 0.12
Nodes (37): addMessage(), createWidget(), disableWidgetInput(), _esc(), fetchConfig(), fetchHistory(), fetchWithTimeout(), formatBookingDate() (+29 more)

### Community 23 - "Voice Calls (Twilio)"
Cohesion: 0.07
Nodes (35): _build_twiml_error(), _build_twiml_gather(), _build_twiml_goodbye(), _build_twiml_greeting(), CallListResponse, CallOut, CallStatsResponse, _find_tenant_by_phone() (+27 more)

### Community 24 - "Auth Endpoint Tests"
Cohesion: 0.07
Nodes (27): _make_auth_token(), Tests for authentication endpoints — signup, login, password reset, and checkout, Test the POST /api/v1/auth/register endpoint., Signing up with an existing email should return 409., New email should create tenant and return 200 with token., Test the POST /api/v1/auth/login endpoint., Login with non-existent email should return 401., Login with correct email but wrong password should return 401. (+19 more)

### Community 25 - "Module 25"
Cohesion: 0.09
Nodes (21): _make_token(), Tests for Client Portal endpoints — service records, portal links, and public po, Test POST /{tenant_id}/service-records., Test GET /{tenant_id}/service-records., Create a JWT signed with the test secret key., Test PUT /{tenant_id}/service-records/{record_id}., Empty update body should return 400., Test DELETE /{tenant_id}/service-records/{record_id}. (+13 more)

### Community 26 - "Module 26"
Cohesion: 0.08
Nodes (23): Tests for login flow, chat endpoint edge cases, and lead capture edge cases.  Us, Test the POST /api/v1/auth/login endpoint — 4 tests., Correct email/password returns 200 with token, tenant_id, etc., Correct email but wrong password returns 401., Login with email not in tenants or team_members returns 401., Request without email or password returns 422 validation error., Test POST /api/v1/widget/chat edge cases — 3 tests., Return table responses for a valid widget+tenant combo. (+15 more)

### Community 27 - "Module 27"
Cohesion: 0.1
Nodes (30): _auth_header(), _make_token(), Tests for the Local SEO Tools endpoints., Tests for GET /api/v1/seo/{tenant_id}., Tests for GET /api/v1/seo/{tenant_id}/keywords., Tests for GET /api/v1/seo/{tenant_id}/dashboard-widget., Configure db_mock.table() to return different data per table name., Unit tests for the _calculate_completeness helper. (+22 more)

### Community 28 - "Module 28"
Cohesion: 0.07
Nodes (18): Enum, detect_intent(), _disambiguate_with_context(), get_intent_summary(), AI-powered intent detection for widget conversations.  Uses lightweight classifi, Use conversation context to pick the most likely intent., Determine if the message should trigger the booking UI.      More conservative t, Get a human-readable summary of the detected intent. (+10 more)

### Community 29 - "Module 29"
Cohesion: 0.08
Nodes (34): client_login(), client_me(), client_register(), ClientLoginRequest, ClientRegisterRequest, _create_client_token(), create_service_record(), delete_service_record() (+26 more)

### Community 30 - "Module 30"
Cohesion: 0.09
Nodes (21): _auth(), _make_token(), _mock_db(), Tests for previously untested messaging/webhook routers.  Covers: email_sequence, Submit with no body should return 422 validation error., test_create_note(), test_create_sequence(), test_facebook_status_no_integration() (+13 more)

### Community 31 - "Module 31"
Cohesion: 0.07
Nodes (25): ai_write_job_description(), AIJobWriteRequest, ApplicationStatusUpdate, create_job(), delete_job(), JobApplicationCreate, JobCreate, JobUpdate (+17 more)

### Community 32 - "Module 32"
Cohesion: 0.06
Nodes (13): Tests for industry-specific presets (pipeline stages, form presets)., Verify aftercare templates cover key industries., Verify rebook intervals for applicable industries., Verify business-profile dashboard defaults for key verticals., Verify pipeline presets cover all major industries., Verify form presets for all industries., Verify reminder extras cover key industries., TestAftercareTemplates (+5 more)

### Community 33 - "Module 33"
Cohesion: 0.11
Nodes (24): OnlineStatusRequest, WidgetConfigResponse, AIFeedbackRequest, delete_ai_feedback(), generate_qr_code(), get_ai_feedback(), get_config(), _get_jwt_claims() (+16 more)

### Community 34 - "Module 34"
Cohesion: 0.07
Nodes (32): Blender Add-on Engineer, Blender Python (bpy), Client-Side Prediction, ENet Transport, Gameplay Ability System (GAS), GDScript 2.0, Godot Gameplay Scripter, Godot Multiplayer Engineer (+24 more)

### Community 35 - "Module 35"
Cohesion: 0.07
Nodes (21): Exception, _OnboardingRecordingDb, _OnboardingRecordingQuery, Regression tests for backend wiring and analytics period handling., Small query double that records onboarding widget updates., Raised by tests to break the infinite automation loop., Preset defaults should not overwrite an already customized widget on re-run., Recurring invoices should run in the 30-minute automation tier. (+13 more)

### Community 36 - "Module 36"
Cohesion: 0.08
Nodes (20): Tests for Cycle 39 quick fixes: holiday hours, lead temperature, score factors., Test that score_lead sets lead_temperature based on score., Create a mock DB that returns lead and conversation data., Unit tests for _get_exception_for_date helper., Test that score_lead returns human-readable factor explanations., Test that generate_available_slots respects exception dates., Build a business_hours config dict., test_closed_holiday_returns_no_slots() (+12 more)

### Community 37 - "Module 37"
Cohesion: 0.09
Nodes (30): booking_page(), booking_submit(), BookingSubmitRequest, _build_booking_page_html(), build_reschedule_url(), _build_service_type_section(), _CancelBody, _fetch_widget_color() (+22 more)

### Community 38 - "Module 38"
Cohesion: 0.07
Nodes (30): CampaignCreate, CampaignTargetFilter, CampaignUpdate, create_campaign(), delete_campaign(), estimate_recipients(), generate_campaign_email(), GenerateEmailRequest (+22 more)

### Community 39 - "Module 39"
Cohesion: 0.09
Nodes (28): create_calendly_event(), Calendly API integration (placeholder for future implementation)., Create a Calendly scheduling link or event.      For MVP, we just return the age, AICampaignRequest, AIGenerateRequest, create_post(), delete_post(), generate_campaign_content() (+20 more)

### Community 40 - "Module 40"
Cohesion: 0.1
Nodes (29): apiFetch(), auto_populate_kb(), autoGenerateKb(), AutoKbFaqEntry, AutoKbRequest, AutoKbResponse, checkoutForWizard(), complete_onboarding() (+21 more)

### Community 41 - "Module 41"
Cohesion: 0.07
Nodes (28): ABTestCreate, ABTestUpdate, ABTestVariantCreate, ABTestVariantUpdate, _assign_lead_to_variant(), _calculate_significance(), complete_ab_test(), create_ab_test() (+20 more)

### Community 42 - "Module 42"
Cohesion: 0.08
Nodes (7): control_center_client(), _make_jwt(), Tests for the Agent Control Center analytics payload., _StaticDb, _StaticQuery, test_control_center_aggregates_wins_risks_and_recovery_queue(), test_control_center_returns_empty_state_when_no_messages()

### Community 43 - "Module 43"
Cohesion: 0.07
Nodes (6): Tests for webhook delivery and retry logic., TestDailyLimit, TestDeliver, TestFireEvent, TestHMACSigning, TestSupportedEvents

### Community 44 - "Module 44"
Cohesion: 0.09
Nodes (21): ContentCreate, ContentUpdate, create_content(), delete_content(), get_content(), list_content(), _parse_platform_versions(), Content Studio endpoints — source content CRUD and AI repurposing. (+13 more)

### Community 45 - "Module 45"
Cohesion: 0.07
Nodes (14): AutomationConfigUpdate, _compute_twilio_signature(), _get_automation(), list_automations(), Automation management — CRUD + Twilio signature verification.  Twilio missed-cal, Fetch a single automation by tenant + type., List all automations for a tenant., Enable or disable an automation. (+6 more)

### Community 46 - "Module 46"
Cohesion: 0.07
Nodes (20): create_stage(), delete_stage(), get_pipeline_analytics(), get_pipeline_board(), list_stages(), move_lead(), MoveleadRequest, Sales pipeline endpoints — stages, board view, analytics, and lead moves. (+12 more)

### Community 47 - "Module 47"
Cohesion: 0.1
Nodes (18): _make_token(), Tests for multi-tenant data isolation.  Verifies that Tenant A cannot access Ten, Tenant A cannot see Tenant B's conversations., Tenant A cannot see Tenant B's appointments., Tenant A cannot modify Tenant B's widget config., Tenant A cannot access Tenant B's dashboard., Tenant A cannot modify Tenant B's settings., Tenant A cannot access Tenant B's billing. (+10 more)

### Community 48 - "Module 48"
Cohesion: 0.09
Nodes (22): _make_jwt(), Tests for appointment endpoints — booking, listing, status updates, cancellation, Test POST /{tenant_id} — booking an appointment with valid data., POST with valid data returns 200 and appointment details., Test POST /{tenant_id} — booking in the past.      The endpoint does not explici, Booking with a past start time still processes (no 500)., Test GET /{tenant_id} — listing appointments., GET returns list of appointments for the tenant. (+14 more)

### Community 49 - "Module 49"
Cohesion: 0.08
Nodes (20): _make_jwt(), Tests for CORS configuration, rate limiting, and automation sequences.  Validate, Create a valid JWT token for test requests., Verify CORSMiddleware configuration in main.py.      The app uses allow_origins=, A request with any Origin header should get Access-Control-Allow-Origin back., With allow_origins=['*'], even unusual origins still get the wildcard header., OPTIONS preflight to /api/v1/widget/chat should return CORS headers., Verify that slowapi rate limiting is configured on key endpoints.      The app u (+12 more)

### Community 50 - "Module 50"
Cohesion: 0.09
Nodes (10): Tests for appointment booking — slot generation and overlap detection., Test double-booking prevention at the slot filtering level., Replicating the overlap check from booking.py., Test that appointments get linked to existing or new leads., Test appointment creation., Test slot generation logic., TestCreateAppointment, TestLeadLinkage (+2 more)

### Community 51 - "Module 51"
Cohesion: 0.09
Nodes (19): _apply_filters(), create_smart_list(), _execute_smart_list_query(), export_smart_list(), get_smart_list_leads(), list_smart_lists(), Smart Lists — dynamic lead segments with filter-based queries and CSV export., Build and execute a leads query for a smart list's filters.      Args:         t (+11 more)

### Community 52 - "Module 52"
Cohesion: 0.1
Nodes (18): _build_sample_payload(), create_webhook(), delete_webhook(), list_events(), list_webhooks(), Webhook management endpoints — CRUD for webhook configurations and delivery logs, Handle incoming SMS via Twilio webhook.      Maps the receiving phone number to, Return all supported webhook events. (+10 more)

### Community 53 - "Module 53"
Cohesion: 0.1
Nodes (19): AIDraftRequest, create_review(), delete_review(), generate_ai_draft(), get_response_stats(), list_reviews(), Reviews management endpoints — Reputation Manager module., Return response history stats for a tenant's reviews.      Includes total/respon (+11 more)

### Community 54 - "Module 54"
Cohesion: 0.07
Nodes (26): ActionItem, AutomationRuleCreate, AutomationRuleUpdate, ConditionItem, create_automation_rule(), delete_automation_rule(), evaluate_automation_trigger(), EvaluateTriggerRequest (+18 more)

### Community 55 - "Module 55"
Cohesion: 0.09
Nodes (17): create_menu_item(), delete_menu_item(), import_menu_from_website(), list_categories(), list_menu_items(), MenuItemCreate, MenuItemUpdate, Menu management endpoints for restaurant tenants. (+9 more)

### Community 56 - "Module 56"
Cohesion: 0.2
Nodes (26): LeadStageUpdate, SequenceCreateRequest, SequenceUpdateRequest, CampaignRequest, create_from_template(), create_sequence(), delete_sequence(), get_sequence_detail() (+18 more)

### Community 57 - "Module 57"
Cohesion: 0.11
Nodes (25): build_oauth_flow(), _build_service(), create_calendar_event(), delete_calendar_event(), delete_integration(), exchange_code(), get_auth_url(), get_busy_times() (+17 more)

### Community 58 - "Module 58"
Cohesion: 0.1
Nodes (25): cancel_appointment(), create_appointment(), create_recurring_series(), generate_available_slots(), get_business_hours(), _get_exception_for_date(), link_appointment_to_lead(), list_appointments() (+17 more)

### Community 59 - "Module 59"
Cohesion: 0.1
Nodes (19): check_waitlist_for_date(), delete_waitlist_entry(), join_waitlist_public(), list_waitlist(), notify_waitlisted_customer(), Appointment waitlist — join, notify, manage waitlisted customers., List waitlist entries for a tenant, optionally filtered by status and date range, Waitlist summary stats. (+11 more)

### Community 60 - "Module 60"
Cohesion: 0.11
Nodes (19): create_flow(), create_from_template(), delete_flow(), flow_analytics(), FlowCreate, FlowUpdate, _get_cached(), list_flows() (+11 more)

### Community 61 - "Module 61"
Cohesion: 0.12
Nodes (25): assign_conversation(), AssignRequest, create_note(), delete_note(), _find_conversation(), get_presence(), list_notes(), NoteCreate (+17 more)

### Community 62 - "Module 62"
Cohesion: 0.13
Nodes (23): check_contradictions(), check_duplicate_info(), check_memory_freshness(), check_stale_references(), generate_dream_report(), generate_summary_line(), get_recent_changed_files(), get_recent_git_log() (+15 more)

### Community 63 - "Module 63"
Cohesion: 0.08
Nodes (13): make_admin_request(), patch_admin_secret(), Tests for platform admin analytics and promotions endpoints., Patch the admin secret in all admin modules., Helper to make authenticated admin requests., No header and no fallback secret should return 401., TestAdminIndustryBreakdown, TestAdminMonthlyGrowth (+5 more)

### Community 64 - "Module 64"
Cohesion: 0.13
Nodes (23): _clean_business_name(), enrich_from_website(), _extract_domain(), _extract_phone_from_text(), gather_prospects(), _is_business_domain(), _is_valid_business_email(), main() (+15 more)

### Community 65 - "Module 65"
Cohesion: 0.11
Nodes (23): _decode_oauth_state(), _encode_oauth_state(), facebook_connection_status(), facebook_disconnect(), facebook_oauth_callback(), facebook_webhook_inbound(), facebook_webhook_verify(), FacebookStatusResponse (+15 more)

### Community 66 - "Module 66"
Cohesion: 0.12
Nodes (20): _allowed_tier_fields(), BusinessPagePublic, BusinessPageSettings, BusinessPageUpdate, _ensure_unique_slug(), get_business_page(), get_business_page_settings(), Business Page endpoints -- public hosted pages and dashboard management. (+12 more)

### Community 67 - "Module 67"
Cohesion: 0.14
Nodes (24): Agency Agents Examples, Agent Handoff Pattern, Aider Integration, Antigravity Integration, Backend Architect (with Memory), Claude Code Integration, Cursor Integration, Gemini CLI Integration (+16 more)

### Community 68 - "Module 68"
Cohesion: 0.11
Nodes (20): add_client_note(), change_client_stage(), _check_tenant(), create_client(), get_client(), get_client_profile(), get_client_timeline(), get_clients() (+12 more)

### Community 69 - "Module 69"
Cohesion: 0.13
Nodes (22): _admin_secret(), _calculate_live_revenue(), get_industry_breakdown(), get_monthly_growth(), get_plan_distribution(), get_platform_overview(), get_promoted_businesses(), get_revenue_trends() (+14 more)

### Community 70 - "Module 70"
Cohesion: 0.17
Nodes (9): _make_jwt(), Tests for documents, item templates, and partial payments.  Uses the same mock p, _setup_table_mock(), TestDocumentCreate, TestDocumentDelete, TestDocumentList, TestDocumentSigning, TestItemTemplates (+1 more)

### Community 71 - "Module 71"
Cohesion: 0.15
Nodes (15): _make_tenant(), _make_widget_config(), Tests for the widget chat API endpoints.  Tests the core widget functionality: c, Test widget config retrieval., Test widget chat endpoint., Test widget health endpoint., Create a FastAPI TestClient with mocked Supabase., _setup_table_mock() (+7 more)

### Community 72 - "Module 72"
Cohesion: 0.12
Nodes (20): _append_unsubscribe_footer(), build_branded_email_html(), _build_tracking_pixel(), build_unsubscribe_url(), _check_rate_limit(), _increment_send_count(), _make_unsub_sig(), Email sending service using Resend API with template rendering and rate limiting (+12 more)

### Community 73 - "Module 73"
Cohesion: 0.15
Nodes (20): connect_repurpose_outputs(), ConnectRequest, create_repurpose_job(), delete_repurpose_job(), get_repurpose_job(), list_repurpose_jobs(), Content Repurpose endpoints — create, list, edit, connect repurpose jobs., List repurpose jobs for a tenant. (+12 more)

### Community 74 - "Module 74"
Cohesion: 0.15
Nodes (17): AvailableNumber, AvailableNumbersResponse, _parse_capabilities(), provision_number(), ProvisionRequest, ProvisionResponse, Business Phone Number Provisioning — search, buy, and release Twilio phone numbe, Search available local phone numbers without buying them. (+9 more)

### Community 75 - "Module 75"
Cohesion: 0.11
Nodes (14): _decode_state(), _encode_state(), google_auth(), google_callback(), google_disconnect(), google_status(), _jwt_secret(), Google Calendar OAuth integration endpoints. (+6 more)

### Community 76 - "Module 76"
Cohesion: 0.11
Nodes (20): ActionItem, create_pipeline_automation(), delete_pipeline_automation(), _execute_create_task_action(), _execute_email_action(), _execute_notify_team_action(), execute_pipeline_automations(), list_pipeline_automations() (+12 more)

### Community 77 - "Module 77"
Cohesion: 0.12
Nodes (7): _make_jwt(), Tests for automation extras: aftercare, rebook, birthday, lead sources., _setup_table_mock(), TestAftercareTemplates, TestLeadSourceAnalytics, TestRebookIntervals, TestReminderExtras

### Community 78 - "Module 78"
Cohesion: 0.13
Nodes (16): _make_jwt(), Tests for Google Calendar OAuth integration endpoints.  Validates the status che, GET /api/v1/integrations/google/status when no integration exists., Should return connected=false when no integration row exists., DELETE /api/v1/integrations/google when no integration exists., Should return gracefully even when no integration row exists., GET /api/v1/integrations/google/status when integration row exists., Should return connected=true with email when integration exists. (+8 more)

### Community 79 - "Module 79"
Cohesion: 0.15
Nodes (17): _auth_header(), _make_token(), Tests for Social Media Marketing and Campaign endpoints., Test AI content generation endpoints., Test marketing campaign CRUD., Test social media post create/list., test_create_campaign_invalid_type(), test_create_email_campaign() (+9 more)

### Community 80 - "Module 80"
Cohesion: 0.13
Nodes (14): action_items_summary(), ActionItemCreate, ActionItemUpdate, create_action_item(), delete_action_item(), list_action_items(), Action items CRUD — AI-extracted tasks from conversations., Create an action item manually. (+6 more)

### Community 81 - "Module 81"
Cohesion: 0.15
Nodes (19): _decode_oauth_state(), disconnect_gbp(), _encode_oauth_state(), gbp_connection_status(), gbp_oauth_callback(), get_gbp_auth_url(), get_gbp_profile(), _jwt_secret() (+11 more)

### Community 82 - "Module 82"
Cohesion: 0.14
Nodes (19): _admin_secret(), check_expires_at(), create_promotion(), delete_promotion(), expire_promotion(), get_promotion(), list_promotions(), PromotionCreate (+11 more)

### Community 83 - "Module 83"
Cohesion: 0.1
Nodes (0): 

### Community 84 - "Module 84"
Cohesion: 0.18
Nodes (8): _make_jwt(), Tests for service types, form presets, and birthday automation., Verify the birthday function can be imported., Verify the month-day matching works., _setup_table_mock(), TestBirthdayAutomation, TestFormPresets, TestServiceTypes

### Community 85 - "Module 85"
Cohesion: 0.12
Nodes (12): _automation_loop(), lifespan(), _process_scheduled_campaigns(), _process_scheduled_posts(), AgentNexLiFy — FastAPI application entry point., Run an automation function with a timeout. Logs results and exceptions., Background loop that runs automation tasks on a tiered schedule.      With multi, Mark marketing campaigns stuck in 'sending' for >30 minutes as 'failed'. (+4 more)

### Community 86 - "Module 86"
Cohesion: 0.18
Nodes (18): call_claude_messages(), call_claude_messages_sync(), ClaudeCallResult, _extract_text(), _extract_usage_value(), _log_error(), _log_finish(), _log_start() (+10 more)

### Community 87 - "Module 87"
Cohesion: 0.15
Nodes (18): connect_outputs(), extract_source(), _extract_title(), _extract_youtube_id(), _is_safe_url(), _parse_repurpose_json(), Content Repurposer Service.  Extracts content from various sources (text, URL, Y, Block internal/private URLs to prevent SSRF. (+10 more)

### Community 88 - "Module 88"
Cohesion: 0.13
Nodes (15): build_memory_prompt(), ConversationMemory, _detect_sentiment(), _extract_facts(), extract_memory_update(), Conversation memory service — maintains running summaries for context window eff, Build a context string combining memory and recent messages.      Strategy: Use, Update conversation memory based on a new exchange.      In production, this wou (+7 more)

### Community 89 - "Module 89"
Cohesion: 0.12
Nodes (19): Account Strategist, Challenger Sale, Deal Strategist, Discovery Coach, FIA Framework, Gap Selling, MEDDPICC, Net Revenue Retention (NRR) (+11 more)

### Community 90 - "Module 90"
Cohesion: 0.15
Nodes (17): _compute_decay(), compute_lead_score(), Lead scoring engine — rule-based 0-100 scoring with engagement, intent, recency,, Score based on how recently the lead was active. Max 20., Compute decay penalty for leads inactive > 7 days., Return (score 1-10, temperature hot/warm/cold) based on lead signals., Score a single lead and persist the result. Returns scoring details., Re-score all leads for a tenant. Returns summary. (+9 more)

### Community 91 - "Module 91"
Cohesion: 0.18
Nodes (17): check_backend_dangerous_imports(), check_code_smells_in_recent_commits(), check_env_safety(), check_frontend_syntax(), check_migration_consistency(), check_uncommitted_changes(), generate_health_report(), main() (+9 more)

### Community 92 - "Module 92"
Cohesion: 0.16
Nodes (15): _auth(), _make_token(), _pass_plan_check(), API-level tests for the content repurposer router.  Validates the full create ->, No-op replacement for _verify_plan., test_create_job(), test_create_job_free_plan_rejected(), test_create_job_invalid_source_type() (+7 more)

### Community 93 - "Module 93"
Cohesion: 0.15
Nodes (17): create_custom_field(), delete_custom_field(), FieldCreate, FieldUpdate, get_lead_custom_fields(), list_custom_fields(), Custom lead fields — per-tenant configurable attributes.  Lets businesses define, Update a custom field definition. (+9 more)

### Community 94 - "Module 94"
Cohesion: 0.14
Nodes (16): _coerce_money(), _extract_bid_request_from_response(), _extract_order_from_response(), _process_bid_request_from_chat(), _process_order_from_chat(), Widget booking-adjacent flows: restaurant order extraction and contractor bid re, Create an order record and send notifications to owner + customer., Extract structured order JSON from AI response, if present and valid. (+8 more)

### Community 95 - "Module 95"
Cohesion: 0.16
Nodes (16): create_scoring_factor(), delete_scoring_factor(), list_scoring_factors(), Lead scoring configuration — per-tenant customizable scoring weights., Create a custom scoring factor., Delete a custom scoring factor., Reset scoring factors to defaults (deletes all custom factors)., Seed default scoring factors for a tenant if none exist. (+8 more)

### Community 96 - "Module 96"
Cohesion: 0.17
Nodes (15): get_action_items(), get_analytics_summary(), _get_tenant_by_api_key(), get_unread_conversations(), list_recent_leads(), list_today_appointments(), AgentNexLiFy MCP Server — exposes business data as tools for AI assistants.  All, List today's appointments.      Args:         api_key: Your AgentNexLiFy MCP API (+7 more)

### Community 97 - "Module 97"
Cohesion: 0.23
Nodes (15): _get_cached(), _parse_dt(), _pct_change(), _period_to_days(), Revenue Analytics — unified financial reporting across invoices, pipeline, order, Daily revenue breakdown for charting., Top customers ranked by total revenue (invoices paid + orders)., Revenue breakdown by source type for pie/donut chart. (+7 more)

### Community 98 - "Module 98"
Cohesion: 0.17
Nodes (14): _get_or_create_sms_conversation(), initiate_sms_conversation(), InitiateSmsRequest, InitiateSmsResponse, _normalize_phone_for_session(), SMS endpoints — send SMS from CRM., Send an outbound SMS from the tenant's provisioned phone number.      Stores the, Send an SMS via Twilio. (+6 more)

### Community 99 - "Module 99"
Cohesion: 0.17
Nodes (9): Tests for Stripe webhook signature verification and event handling., Test that different Stripe event types are routed to correct handlers., Test that the Stripe webhook endpoint validates signatures correctly., test_payment_failed_routed(), test_subscription_deleted_routed(), test_subscription_updated_routed(), test_unhandled_event_still_returns_ok(), TestStripeEventRouting (+1 more)

### Community 100 - "Module 100"
Cohesion: 0.18
Nodes (14): create_tag_definition(), delete_tag_definition(), _ensure_system_tags(), list_tag_definitions(), Tag definitions CRUD — manage AI conversation auto-categorization tags., Update a tag definition. System tags can only toggle is_enabled., Delete a custom tag definition. System tags cannot be deleted., Seed system tags for a tenant if they don't exist yet. (+6 more)

### Community 101 - "Module 101"
Cohesion: 0.18
Nodes (14): create_order(), get_order(), list_orders(), order_stats(), OrderCreate, OrderStatusUpdate, Order management endpoints for restaurant tenants., Create a new order (usually from the chat widget flow). (+6 more)

### Community 102 - "Module 102"
Cohesion: 0.14
Nodes (13): Tests for the content repurposer service., Only requested formats are returned., Plain text source returns content as-is with word count., HTML tags are stripped from text/podcast sources., Localhost and private URLs are rejected with ValueError., YouTube extraction mocks the transcript API and joins text entries., When no format filter is given, all 5 format keys are present., test_extract_source_text() (+5 more)

### Community 103 - "Module 103"
Cohesion: 0.14
Nodes (4): Focused tests for recent AI runtime hardening work.  Covers: - widget structured, TestWidgetPromptHardening, TestWidgetStructuredPayloadValidation, TestWrapperCentralization

### Community 104 - "Module 104"
Cohesion: 0.26
Nodes (11): build_spreadsheet(), clean_email(), clean_phone(), extract_business_name(), main(), AgentNexLiFy Prospect List Builder Tries 3 approaches in order:   1. googlesearc, Visit a URL and extract phone/email via regex., Try to clean a page title into a business name. (+3 more)

### Community 105 - "Module 105"
Cohesion: 0.28
Nodes (12): _count_sentences(), EvalResult, EvalScenario, _evaluate_quality(), _extract_response_text(), _load_scenarios(), main(), _parse_args() (+4 more)

### Community 106 - "Module 106"
Cohesion: 0.19
Nodes (12): _cf_headers(), _execute_crawl(), get_crawl_status(), get_crawled_content(), _is_safe_url(), Website crawling service using Cloudflare Browser Rendering API.  Crawls a tenan, Call Cloudflare Browser Rendering /crawl endpoint and store results., Get the latest crawl status for a tenant. (+4 more)

### Community 107 - "Module 107"
Cohesion: 0.22
Nodes (12): create_template(), delete_template(), list_templates(), preview_template(), Email templates API — reusable template library for automation sequences., List all email templates (starter + tenant custom)., Create a custom email template., Update a custom email template. (+4 more)

### Community 108 - "Module 108"
Cohesion: 0.17
Nodes (11): mock_httpx_batch_response(), mock_httpx_response(), Tests for the embedding service., Mock a successful Voyage AI embedding response., Mock a successful batch embedding response., embed_text returns a 1024-dimension float list., embed_batch returns one vector per input text., embed_text truncates input longer than MAX_EMBED_CHARS. (+3 more)

### Community 109 - "Module 109"
Cohesion: 0.2
Nodes (4): ensure_directory(), relative_path(), skill_source_from_path(), write_json()

### Community 110 - "Module 110"
Cohesion: 0.35
Nodes (11): _clean_business_name(), enrich(), _extract_domain(), _extract_phone(), is_bad_email(), is_bad_name(), _is_business_domain(), _is_valid_email() (+3 more)

### Community 111 - "Module 111"
Cohesion: 0.27
Nodes (10): build_viewer_data(), coerce_date(), count_words(), extract_cross_refs(), main(), parse_frontmatter(), Extract [[slug]] cross-references from article body., Count words in text, stripping markdown syntax. (+2 more)

### Community 112 - "Module 112"
Cohesion: 0.27
Nodes (10): _check_daily_limit(), _deliver(), fire_event(), fire_event_background(), _increment_daily(), Webhook dispatcher — delivers event payloads to registered webhook URLs., POST payload to a single webhook URL. Log result. Retry up to 3 times with expon, Fire webhook event from a sync context by scheduling on the running event loop. (+2 more)

### Community 113 - "Module 113"
Cohesion: 0.2
Nodes (1): Focused parser tests for local SEO AI JSON helpers.

### Community 114 - "Module 114"
Cohesion: 0.29
Nodes (9): _find_tenant_by_phone(), handle_inbound_sms(), handle_missed_call(), Twilio webhook endpoints — missed call text-back and inbound SMS handling.  When, Twilio messaging webhook — handles inbound SMS replies.      When a caller repli, Verify Twilio webhook signature (X-Twilio-Signature header)., Look up tenant by their configured notification_phone or Twilio number., Twilio voice webhook — triggered when a call goes unanswered.      Sends an auto (+1 more)

### Community 115 - "Module 115"
Cohesion: 0.24
Nodes (9): csat_stats(), list_csat_responses(), CSAT/NPS satisfaction survey endpoints.  Auto-sends satisfaction surveys after c, CSAT dashboard stats: avg rating, count, distribution, trend., List all CSAT responses., Public endpoint — customer submits their CSAT rating., submit_survey(), SurveySubmit (+1 more)

### Community 116 - "Module 116"
Cohesion: 0.31
Nodes (8): _check_tenant(), get_notifications(), Dashboard notifications center — aggregates recent activity into a single feed., Send notification to the real estate agent via email (and SMS if configured)., Get aggregated notifications for the dashboard bell., send_agent_notification(), _send_email(), _send_sms()

### Community 117 - "Module 117"
Cohesion: 0.47
Nodes (8): changed_files(), is_js_source(), is_python_source(), main(), parse_args(), run(), run_diff_cover(), write_diff_file()

### Community 118 - "Module 118"
Cohesion: 0.39
Nodes (8): _duration(), _filter_entries(), _load_input_lines(), main(), _parse_args(), _parse_entries(), _percentile(), Summarize recent Railway HTTP latency from JSON log lines.  Examples:     python

### Community 119 - "Module 119"
Cohesion: 0.25
Nodes (9): AI Manifest (.ai/manifest.json), Claude Skills (.claude/skills/), Codex Skills (.codex/skills/), Prompt Library (PROMPTLIBRARY.md), Agent Control Plane Canonical Hierarchy, Developer Agent System (CLAUDE.md/.ai/manifest.json), Claudeopedia — LLM Wiki Knowledge Base System, Versioned Reusable Prompts Pattern (+1 more)

### Community 120 - "Module 120"
Cohesion: 0.22
Nodes (9): Adaptive Music System, Blockout Discipline, Encounter Design, Environmental Storytelling, FMOD, Game Audio Engineer, Level Designer, Spatial Audio (+1 more)

### Community 121 - "Module 121"
Cohesion: 0.25
Nodes (3): handle_tool_call(), Functions that execute when Claude calls a tool., Dispatch a tool call to the appropriate handler. Returns the tool result as a st

### Community 122 - "Module 122"
Cohesion: 0.25
Nodes (1): Tests for centralized LLM runtime logging/safety behavior.

### Community 123 - "Module 123"
Cohesion: 0.36
Nodes (4): handleConnect(), handleDisconnect(), showMainView(), showSettingsView()

### Community 124 - "Module 124"
Cohesion: 0.36
Nodes (7): get_dashboard_business_profile(), get_widget_defaults(), humanize_business_type(), Business-type-aware defaults for widgets and dashboard personalization., Return widget defaults for the given business type., Return a dashboard-facing preset summary for a tenant., resolve_business_profile_key()

### Community 125 - "Module 125"
Cohesion: 0.25
Nodes (7): embed_batch(), embed_query(), embed_text(), Embedding service for knowledge base semantic search.  Uses Voyage AI (voyage-3-, Embed a single text string. Returns 512-dim vector., Embed multiple texts in one API call. Returns list of 512-dim vectors., Embed a search query. Uses input_type='query' for better retrieval.

### Community 126 - "Module 126"
Cohesion: 0.25
Nodes (7): format_textback_message(), looks_like_booking_request(), Twilio service — missed-call text-back and SMS utilities.  Production webhook UR, Send an SMS via the Twilio REST API., Interpolate {business_name} into the text-back template., Return True if the message contains booking-related keywords., send_sms()

### Community 127 - "Module 127"
Cohesion: 0.25
Nodes (7): crawl_content(), crawl_status(), Website crawl endpoints — start crawl, check status, get content., Start a website crawl for the tenant's website URL., Get the latest crawl status for a tenant., Get the extracted website content (for AI knowledge base preview)., trigger_crawl()

### Community 128 - "Module 128"
Cohesion: 0.32
Nodes (7): _handle_bounce(), Resend webhook endpoint for email event handling (bounces, complaints).  Handles, Mark the lead's email as bounced, scoped to the originating tenant.      Looks u, Verify Resend webhook signature using the svix headers.      Returns True when v, Handle Resend webhook events.      Supported events:     - email.bounced: marks, resend_webhook(), _verify_resend_signature()

### Community 129 - "Module 129"
Cohesion: 0.32
Nodes (7): get_wizard_stats(), log_wizard_event(), Wizard drop-off tracking — lightweight analytics for onboarding funnel., Log a wizard step event for drop-off tracking., Get wizard completion funnel stats., _verify_tenant(), WizardEvent

### Community 130 - "Module 130"
Cohesion: 0.25
Nodes (8): Implementation Discipline (minimal change principle), Backend Dev Agent, Compound Engineering 5-Agent Pipeline, DevOps Agent, Frontend Dev Agent, QA Tester Agent, Schema Guardian Agent, LLM Council (5 AI Advisor Decision Framework)

### Community 131 - "Module 131"
Cohesion: 0.29
Nodes (1): Focused parser-seam tests for AI-generated route outputs.

### Community 132 - "Module 132"
Cohesion: 0.29
Nodes (1): Focused tests for content repurposer JSON parsing / repair helpers.

### Community 133 - "Module 133"
Cohesion: 0.43
Nodes (6): check_sms_rate_limit(), get_sms_usage(), increment_sms_count(), _maybe_reset(), SMS rate limiting — in-memory daily tracking per tenant., Return True if tenant is within daily SMS limit.

### Community 134 - "Module 134"
Cohesion: 0.29
Nodes (0): 

### Community 135 - "Module 135"
Cohesion: 0.33
Nodes (5): get_business_context(), Shared FastAPI dependencies for AgentNexLiFy backend.  Contains utilities that w, Verify the JWT claims match the requested tenant. Raises 403 if not., Fetch business name and type from the tenants table for AI context.      Returns, verify_tenant()

### Community 136 - "Module 136"
Cohesion: 0.4
Nodes (4): _ensure_initialized(), get_or_create_customer(), Stripe client singleton and billing helpers., Find existing Stripe customer by tenant metadata, or create one.

### Community 137 - "Module 137"
Cohesion: 0.33
Nodes (5): Widget lead capture endpoints: POST /lead and POST /offline-contact.  WARNING: P, Submit contact form when widget is in offline mode. Creates a lead., Manually submit or update lead information from the widget., submit_lead(), submit_offline_contact()

### Community 138 - "Module 138"
Cohesion: 0.4
Nodes (5): _handle_invoice_payment(), Stripe webhook endpoint at /api/v1/webhooks/stripe.  Delegates to the same handl, Handle Stripe webhook events via /api/v1/webhooks/stripe., Handle payment for an AgentNexLiFy invoice (via Stripe Payment Link).      Updat, stripe_webhook()

### Community 139 - "Module 139"
Cohesion: 0.4
Nodes (1): Tests for selective retry adoption in non-latency-critical AI paths.

### Community 140 - "Module 140"
Cohesion: 0.4
Nodes (1): Targeted tests for centralized onboarding AI paths and parser behavior.

### Community 141 - "Module 141"
Cohesion: 0.4
Nodes (3): Safe asyncio task creation with error logging.  Prevents the silent-failure patt, Like asyncio.create_task() but logs exceptions instead of swallowing them., safe_create_task()

### Community 142 - "Module 142"
Cohesion: 0.5
Nodes (5): Dual Schema Architectural Split Issue, Dead Code Archive (_archive/ directory), Multi-Tenant Migration Schema (tenants table), Old Single-Tenant Schema (clients table), Full Audit (2026-03-09, 128 issues found)

### Community 143 - "Module 143"
Cohesion: 0.67
Nodes (3): main(), _print_summary(), One-off test: simulate and send the weekly digest email for MTOptions tenant.  U

### Community 144 - "Module 144"
Cohesion: 0.5
Nodes (0): 

### Community 145 - "Module 145"
Cohesion: 0.5
Nodes (2): BaseSettings, Settings

### Community 146 - "Module 146"
Cohesion: 0.5
Nodes (3): log_activity(), Activity logging service — fire-and-forget, never raises., Insert a row into activity_log. Silently swallows errors.

### Community 147 - "Module 147"
Cohesion: 0.5
Nodes (3): Retry utility for transient external service failures (Anthropic, Resend, Twilio, Call fn() with exponential backoff retries on transient errors.      Retries on:, with_retry()

### Community 148 - "Module 148"
Cohesion: 0.5
Nodes (3): ingest_channel_message(), Omnichannel message ingestion layer.  Schema notes (confirmed by live schema and, Normalize and store an inbound channel message (legacy path).      Args:

### Community 149 - "Module 149"
Cohesion: 0.5
Nodes (3): Public support / contact-us endpoint., Accept a public contact-form submission., submit_contact()

### Community 150 - "Module 150"
Cohesion: 0.5
Nodes (3): list_webhook_deliveries(), Webhook delivery log endpoint — shows recent deliveries per webhook., Return recent webhook_logs for a specific webhook.

### Community 151 - "Module 151"
Cohesion: 0.67
Nodes (2): getPresetWidgetDefaults(), resolvePresetKey()

### Community 152 - "Module 152"
Cohesion: 0.5
Nodes (4): High Definition Render Pipeline (HDRP), Unity Shader Graph, Universal Render Pipeline (URP), Unity Shader Graph Artist

### Community 153 - "Module 153"
Cohesion: 0.67
Nodes (1): Seed the MTOptions Welcome Sequence in email_sequences.  Looks up the MTOptions

### Community 154 - "Module 154"
Cohesion: 0.67
Nodes (2): _get_real_client_ip(), Extract the real client IP behind Railway's proxy.      Railway (and most revers

### Community 155 - "Module 155"
Cohesion: 0.67
Nodes (3): React/Vite Dashboard Frontend, Vercel Frontend Hosting, Content Studio Feature Shipped (2026-03-13, 46 commits)

### Community 156 - "Module 156"
Cohesion: 0.67
Nodes (3): MCP Server (tenant data as tools), MCP Auth Tightening (dedicated API keys), Safety-First Hardening Pass (2026-04-05)

### Community 157 - "Module 157"
Cohesion: 0.67
Nodes (3): Routine Safety Boundary (docs/ writes only), Evening Auto Routine (scripts/daily/evening-auto.sh), Morning Auto Routine (scripts/daily/morning-auto.sh)

### Community 158 - "Module 158"
Cohesion: 0.67
Nodes (3): ScriptableObjects, Unity Architect, Unity Editor Tool Developer

### Community 159 - "Module 159"
Cohesion: 0.67
Nodes (3): Design Token System, UI Designer, WCAG AA Standards

### Community 160 - "Module 160"
Cohesion: 1.0
Nodes (0): 

### Community 161 - "Module 161"
Cohesion: 1.0
Nodes (0): 

### Community 162 - "Module 162"
Cohesion: 1.0
Nodes (0): 

### Community 163 - "Module 163"
Cohesion: 1.0
Nodes (1): Claude tool-use schema definitions for the real estate chatbot.

### Community 164 - "Module 164"
Cohesion: 1.0
Nodes (0): 

### Community 165 - "Module 165"
Cohesion: 1.0
Nodes (2): Current Task: Rotate Compromised Railway API Key, Security Incident: API Key Committed to .env.example

### Community 166 - "Module 166"
Cohesion: 1.0
Nodes (2): Proposal Strategist, Win Theme Development

### Community 167 - "Module 167"
Cohesion: 1.0
Nodes (0): 

### Community 168 - "Module 168"
Cohesion: 1.0
Nodes (0): 

### Community 169 - "Module 169"
Cohesion: 1.0
Nodes (1): Message at max_length (10000 chars) should be accepted.

### Community 170 - "Module 170"
Cohesion: 1.0
Nodes (1): Valid API key should return widget config.

### Community 171 - "Module 171"
Cohesion: 1.0
Nodes (1): When a profile already exists, it should update (not insert).

### Community 172 - "Module 172"
Cohesion: 1.0
Nodes (1): A date marked closed in exceptions should return zero slots.

### Community 173 - "Module 173"
Cohesion: 1.0
Nodes (1): A date with open/close override should use those hours instead of normal day hou

### Community 174 - "Module 174"
Cohesion: 1.0
Nodes (1): Days not in exceptions should use normal hours.

### Community 175 - "Module 175"
Cohesion: 1.0
Nodes (1): Lead with email + phone + pricing + availability + recent = hot.

### Community 176 - "Module 176"
Cohesion: 1.0
Nodes (1): Lead with email + name + some messages = warm.

### Community 177 - "Module 177"
Cohesion: 1.0
Nodes (1): Lead with minimal info = cold.

### Community 178 - "Module 178"
Cohesion: 1.0
Nodes (1): Factors list includes email and phone when present.

### Community 179 - "Module 179"
Cohesion: 1.0
Nodes (1): Factors list includes intent keywords when user asked about pricing.

### Community 180 - "Module 180"
Cohesion: 1.0
Nodes (1): Result dict always has factors and temperature keys.

### Community 181 - "Module 181"
Cohesion: 1.0
Nodes (1): Free plan should not access repurposer.

### Community 182 - "Module 182"
Cohesion: 1.0
Nodes (1): One due execution → execute_step called once → returns 1.

### Community 183 - "Module 183"
Cohesion: 1.0
Nodes (1): Empty result from DB → returns 0 without calling execute_step.

### Community 184 - "Module 184"
Cohesion: 1.0
Nodes (1): Three due executions → execute_step called three times → returns 3.

### Community 185 - "Module 185"
Cohesion: 1.0
Nodes (1): If execute_step raises on first execution, the second one still runs.

### Community 186 - "Module 186"
Cohesion: 1.0
Nodes (1): Matching sequence + first step → creates execution row → returns 1.

### Community 187 - "Module 187"
Cohesion: 1.0
Nodes (1): Sequence targets 'closed' but new_stage='contacted' → no enrollment → 0.

### Community 188 - "Module 188"
Cohesion: 1.0
Nodes (1): No sequences for this tenant+trigger → returns 0 immediately.

### Community 189 - "Module 189"
Cohesion: 1.0
Nodes (1): DB insert raises (UNIQUE constraint) → caught, enrollment count stays 0.

### Community 190 - "Module 190"
Cohesion: 1.0
Nodes (1): Invoice past due_date → status updated to 'overdue' + email reminder sent.

### Community 191 - "Module 191"
Cohesion: 1.0
Nodes (1): Invoice due tomorrow → email reminder sent with 'tomorrow' in subject.

### Community 192 - "Module 192"
Cohesion: 1.0
Nodes (1): activity_log dedup hit for today → email NOT sent → returns 0.

### Community 193 - "Module 193"
Cohesion: 1.0
Nodes (1): Invoice with lead_id=None → skipped early without crash or email.

### Community 194 - "Module 194"
Cohesion: 1.0
Nodes (1): Non-Monday weekday → returns 0, no email sent.          Note: get_supabase IS ca

### Community 195 - "Module 195"
Cohesion: 1.0
Nodes (1): Monday + paid tenant + no dedup hit → email sent → returns 1.

### Community 196 - "Module 196"
Cohesion: 1.0
Nodes (1): Monday but dedup hit in activity_log → returns 0, no email sent.

### Community 197 - "Module 197"
Cohesion: 1.0
Nodes (1): Free-plan tenants are excluded by .neq('plan', 'free') at the DB level.

### Community 198 - "Module 198"
Cohesion: 1.0
Nodes (1): If another worker advances the parent first, no duplicate child invoice is creat

### Community 199 - "Module 199"
Cohesion: 1.0
Nodes (1): If child invoice creation fails after the claim, next_invoice_date is restored.

### Community 200 - "Module 200"
Cohesion: 1.0
Nodes (1): Lead created 25h ago with no conversation → trigger_sequence called.

### Community 201 - "Module 201"
Cohesion: 1.0
Nodes (1): Lead has a message within the last 24h → skip, trigger_sequence NOT called.

### Community 202 - "Module 202"
Cohesion: 1.0
Nodes (1): Lead already has an in_progress execution for a no_response_24h sequence.

### Community 203 - "Module 203"
Cohesion: 1.0
Nodes (1): No new leads older than 24h returns 0 and does not trigger a sequence.

### Community 204 - "Module 204"
Cohesion: 1.0
Nodes (1): Rule execution should load lead data using the rule tenant before actions.

### Community 205 - "Module 205"
Cohesion: 1.0
Nodes (1): Sequence enrollment actions need current_step and next_run_at.

### Community 206 - "Module 206"
Cohesion: 1.0
Nodes (1): Public endpoint — no auth needed, uses api_key.

### Community 207 - "Module 207"
Cohesion: 1.0
Nodes (1): Public endpoint — token format is tenant_id:session_id.

### Community 208 - "Module 208"
Cohesion: 1.0
Nodes (1): Slots overlapping with existing appointments should be excluded.

### Community 209 - "Module 209"
Cohesion: 1.0
Nodes (1): Buffer minutes should increase the step between slots.

### Community 210 - "Module 210"
Cohesion: 1.0
Nodes (1): When no lead exists for the email, creates a new one with client_id.

### Community 211 - "Module 211"
Cohesion: 1.0
Nodes (1): Twilio webhooks require valid signature — unsigned requests fail.

### Community 212 - "Module 212"
Cohesion: 1.0
Nodes (0): 

### Community 213 - "Module 213"
Cohesion: 1.0
Nodes (1): Deserialize from JSON stored in database.

### Community 214 - "Module 214"
Cohesion: 1.0
Nodes (0): 

### Community 215 - "Module 215"
Cohesion: 1.0
Nodes (1): KAIROS Dream Log (contradictions and stale refs)

### Community 216 - "Module 216"
Cohesion: 1.0
Nodes (1): Autonomous Optimization Architect

### Community 217 - "Module 217"
Cohesion: 1.0
Nodes (1): Frontend Developer

### Community 218 - "Module 218"
Cohesion: 1.0
Nodes (1): CMS Developer

### Community 219 - "Module 219"
Cohesion: 1.0
Nodes (1): Git Workflow Master

### Community 220 - "Module 220"
Cohesion: 1.0
Nodes (1): Rapid Prototyper

### Community 221 - "Module 221"
Cohesion: 1.0
Nodes (1): Solidity Smart Contract Engineer

### Community 222 - "Module 222"
Cohesion: 1.0
Nodes (1): Data Engineer

### Community 223 - "Module 223"
Cohesion: 1.0
Nodes (1): Threat Detection Engineer

### Community 224 - "Module 224"
Cohesion: 1.0
Nodes (1): Technical Writer

### Community 225 - "Module 225"
Cohesion: 1.0
Nodes (1): Senior Developer

### Community 226 - "Module 226"
Cohesion: 1.0
Nodes (1): Filament Optimization Specialist

### Community 227 - "Module 227"
Cohesion: 1.0
Nodes (1): Software Architect

### Community 228 - "Module 228"
Cohesion: 1.0
Nodes (1): Email Intelligence Engineer

### Community 229 - "Module 229"
Cohesion: 1.0
Nodes (1): Code Reviewer

### Community 230 - "Module 230"
Cohesion: 1.0
Nodes (1): AI Engineer

### Community 231 - "Module 231"
Cohesion: 1.0
Nodes (1): Feishu Integration Developer

### Community 232 - "Module 232"
Cohesion: 1.0
Nodes (1): Mobile App Builder

### Community 233 - "Module 233"
Cohesion: 1.0
Nodes (1): WeChat Mini Program Developer

### Community 234 - "Module 234"
Cohesion: 1.0
Nodes (1): Security Engineer

### Community 235 - "Module 235"
Cohesion: 1.0
Nodes (1): Terminal Integration Specialist

### Community 236 - "Module 236"
Cohesion: 1.0
Nodes (1): XR Cockpit Interaction Specialist

### Community 237 - "Module 237"
Cohesion: 1.0
Nodes (1): XR Interface Architect

### Community 238 - "Module 238"
Cohesion: 1.0
Nodes (1): XR Immersive Developer

### Community 239 - "Module 239"
Cohesion: 1.0
Nodes (1): visionOS Spatial Engineer

### Community 240 - "Module 240"
Cohesion: 1.0
Nodes (1): macOS Spatial/Metal Engineer

### Community 241 - "Module 241"
Cohesion: 1.0
Nodes (1): Engineering Agents Category

### Community 242 - "Module 242"
Cohesion: 1.0
Nodes (1): Spatial Computing Agents Category

### Community 243 - "Module 243"
Cohesion: 1.0
Nodes (1): Shadow Testing / Dark Launching

### Community 244 - "Module 244"
Cohesion: 1.0
Nodes (1): Circuit Breaker Pattern

### Community 245 - "Module 245"
Cohesion: 1.0
Nodes (1): Medallion Architecture

### Community 246 - "Module 246"
Cohesion: 1.0
Nodes (1): Detection-as-Code

### Community 247 - "Module 247"
Cohesion: 1.0
Nodes (1): MITRE ATT&CK Framework

### Community 248 - "Module 248"
Cohesion: 1.0
Nodes (1): UUPS Upgradeable Proxy Pattern

### Community 249 - "Module 249"
Cohesion: 1.0
Nodes (1): Checks-Effects-Interactions Pattern

### Community 250 - "Module 250"
Cohesion: 1.0
Nodes (1): WCAG 2.1 AA Compliance

### Community 251 - "Module 251"
Cohesion: 1.0
Nodes (1): Core Web Vitals

### Community 252 - "Module 252"
Cohesion: 1.0
Nodes (1): STRIDE Threat Modeling

### Community 253 - "Module 253"
Cohesion: 1.0
Nodes (1): Zero-Trust Architecture

### Community 254 - "Module 254"
Cohesion: 1.0
Nodes (1): Architecture Decision Record (ADR)

### Community 255 - "Module 255"
Cohesion: 1.0
Nodes (1): Domain-Driven Design — Bounded Context

### Community 256 - "Module 256"
Cohesion: 1.0
Nodes (1): Sigma Detection Rules

### Community 257 - "Module 257"
Cohesion: 1.0
Nodes (1): OpenZeppelin

### Community 258 - "Module 258"
Cohesion: 1.0
Nodes (1): Foundry

### Community 259 - "Module 259"
Cohesion: 1.0
Nodes (1): Apache Spark / PySpark

### Community 260 - "Module 260"
Cohesion: 1.0
Nodes (1): dbt (data build tool)

### Community 261 - "Module 261"
Cohesion: 1.0
Nodes (1): Delta Lake

### Community 262 - "Module 262"
Cohesion: 1.0
Nodes (1): SwiftTerm

### Community 263 - "Module 263"
Cohesion: 1.0
Nodes (1): Apple Metal API

### Community 264 - "Module 264"
Cohesion: 1.0
Nodes (1): WebXR Device API

### Community 265 - "Module 265"
Cohesion: 1.0
Nodes (1): RealityKit

### Community 266 - "Module 266"
Cohesion: 1.0
Nodes (1): Compositor Services (visionOS)

### Community 267 - "Module 267"
Cohesion: 1.0
Nodes (1): Feishu/Lark Open Platform SDK

### Community 268 - "Module 268"
Cohesion: 1.0
Nodes (1): Filament PHP

### Community 269 - "Module 269"
Cohesion: 1.0
Nodes (0): 

### Community 270 - "Module 270"
Cohesion: 1.0
Nodes (1): Demo Script — Generic 2026-04-01

### Community 271 - "Module 271"
Cohesion: 1.0
Nodes (1): Demo Script — Coffee Shop 2026-03-12

### Community 272 - "Module 272"
Cohesion: 1.0
Nodes (1): Help Article: Managing Your Leads

### Community 273 - "Module 273"
Cohesion: 1.0
Nodes (1): Help Article: Widget FAQ

### Community 274 - "Module 274"
Cohesion: 1.0
Nodes (1): Help Article: How to Embed the Widget

### Community 275 - "Module 275"
Cohesion: 1.0
Nodes (1): Help Article: Birthday Automation

### Community 276 - "Module 276"
Cohesion: 1.0
Nodes (1): Help Article: Documents & E-Signatures

### Community 277 - "Module 277"
Cohesion: 1.0
Nodes (1): Help Article: Setting Up Appointment Booking

### Community 278 - "Module 278"
Cohesion: 1.0
Nodes (1): Help Article: Managing Your Sales Pipeline

### Community 279 - "Module 279"
Cohesion: 1.0
Nodes (1): Help Article: Understanding Your Analytics Dashboard

### Community 280 - "Module 280"
Cohesion: 1.0
Nodes (1): Help Article: Form Presets

### Community 281 - "Module 281"
Cohesion: 1.0
Nodes (1): Help Article: How to Configure Your AI Assistant

### Community 282 - "Module 282"
Cohesion: 1.0
Nodes (1): Help Article: Service Types for Booking

### Community 283 - "Module 283"
Cohesion: 1.0
Nodes (1): Landing Page: Case Study Template

### Community 284 - "Module 284"
Cohesion: 1.0
Nodes (1): Landing Page: A/B Test Headlines

### Community 285 - "Module 285"
Cohesion: 1.0
Nodes (1): Social Media Posts — LinkedIn & Facebook

### Community 286 - "Module 286"
Cohesion: 1.0
Nodes (1): Email: Welcome (Day 0)

### Community 287 - "Module 287"
Cohesion: 1.0
Nodes (1): Email: Day 7 Check-In

### Community 288 - "Module 288"
Cohesion: 1.0
Nodes (1): Email: Day 14 Upgrade Prompt

### Community 289 - "Module 289"
Cohesion: 1.0
Nodes (1): Lead Scoring

### Community 290 - "Module 290"
Cohesion: 1.0
Nodes (1): Widget Appointment Booking

### Community 291 - "Module 291"
Cohesion: 1.0
Nodes (1): Birthday Automation

### Community 292 - "Module 292"
Cohesion: 1.0
Nodes (1): Chat Flow Builder

### Community 293 - "Module 293"
Cohesion: 1.0
Nodes (1): Form Presets

### Community 294 - "Module 294"
Cohesion: 1.0
Nodes (1): Documents & E-Signatures

### Community 295 - "Module 295"
Cohesion: 1.0
Nodes (1): Sales Pipeline (Kanban)

### Community 296 - "Module 296"
Cohesion: 1.0
Nodes (1): Analytics Dashboard

### Community 297 - "Module 297"
Cohesion: 1.0
Nodes (1): Demo Features to Skip (Internal)

## Knowledge Gaps
- **1033 isolated node(s):** `SMS endpoints — send SMS from CRM.`, `Send an SMS via Twilio.`, `Lead scoring engine — rule-based 0-100 scoring with engagement, intent, recency,`, `Return (score 1-10, temperature hot/warm/cold) based on lead signals.`, `Calendly API integration (placeholder for future implementation).` (+1028 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Module 160`** (2 nodes): `seed_demo_client.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 161`** (2 nodes): `setup_supabase.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 162`** (2 nodes): `test_conversation.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 163`** (2 nodes): `tool_definitions.py`, `Claude tool-use schema definitions for the real estate chatbot.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 164`** (2 nodes): `database.py`, `get_supabase()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 165`** (2 nodes): `Current Task: Rotate Compromised Railway API Key`, `Security Incident: API Key Committed to .env.example`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 166`** (2 nodes): `Proposal Strategist`, `Win Theme Development`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 167`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 168`** (1 nodes): `demoConfig.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 169`** (1 nodes): `Message at max_length (10000 chars) should be accepted.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 170`** (1 nodes): `Valid API key should return widget config.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 171`** (1 nodes): `When a profile already exists, it should update (not insert).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 172`** (1 nodes): `A date marked closed in exceptions should return zero slots.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 173`** (1 nodes): `A date with open/close override should use those hours instead of normal day hou`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 174`** (1 nodes): `Days not in exceptions should use normal hours.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 175`** (1 nodes): `Lead with email + phone + pricing + availability + recent = hot.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 176`** (1 nodes): `Lead with email + name + some messages = warm.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 177`** (1 nodes): `Lead with minimal info = cold.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 178`** (1 nodes): `Factors list includes email and phone when present.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 179`** (1 nodes): `Factors list includes intent keywords when user asked about pricing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 180`** (1 nodes): `Result dict always has factors and temperature keys.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 181`** (1 nodes): `Free plan should not access repurposer.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 182`** (1 nodes): `One due execution → execute_step called once → returns 1.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 183`** (1 nodes): `Empty result from DB → returns 0 without calling execute_step.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 184`** (1 nodes): `Three due executions → execute_step called three times → returns 3.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 185`** (1 nodes): `If execute_step raises on first execution, the second one still runs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 186`** (1 nodes): `Matching sequence + first step → creates execution row → returns 1.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 187`** (1 nodes): `Sequence targets 'closed' but new_stage='contacted' → no enrollment → 0.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 188`** (1 nodes): `No sequences for this tenant+trigger → returns 0 immediately.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 189`** (1 nodes): `DB insert raises (UNIQUE constraint) → caught, enrollment count stays 0.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 190`** (1 nodes): `Invoice past due_date → status updated to 'overdue' + email reminder sent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 191`** (1 nodes): `Invoice due tomorrow → email reminder sent with 'tomorrow' in subject.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 192`** (1 nodes): `activity_log dedup hit for today → email NOT sent → returns 0.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 193`** (1 nodes): `Invoice with lead_id=None → skipped early without crash or email.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 194`** (1 nodes): `Non-Monday weekday → returns 0, no email sent.          Note: get_supabase IS ca`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 195`** (1 nodes): `Monday + paid tenant + no dedup hit → email sent → returns 1.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 196`** (1 nodes): `Monday but dedup hit in activity_log → returns 0, no email sent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 197`** (1 nodes): `Free-plan tenants are excluded by .neq('plan', 'free') at the DB level.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 198`** (1 nodes): `If another worker advances the parent first, no duplicate child invoice is creat`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 199`** (1 nodes): `If child invoice creation fails after the claim, next_invoice_date is restored.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 200`** (1 nodes): `Lead created 25h ago with no conversation → trigger_sequence called.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 201`** (1 nodes): `Lead has a message within the last 24h → skip, trigger_sequence NOT called.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 202`** (1 nodes): `Lead already has an in_progress execution for a no_response_24h sequence.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 203`** (1 nodes): `No new leads older than 24h returns 0 and does not trigger a sequence.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 204`** (1 nodes): `Rule execution should load lead data using the rule tenant before actions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 205`** (1 nodes): `Sequence enrollment actions need current_step and next_run_at.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 206`** (1 nodes): `Public endpoint — no auth needed, uses api_key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 207`** (1 nodes): `Public endpoint — token format is tenant_id:session_id.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 208`** (1 nodes): `Slots overlapping with existing appointments should be excluded.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 209`** (1 nodes): `Buffer minutes should increase the step between slots.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 210`** (1 nodes): `When no lead exists for the email, creates a new one with client_id.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 211`** (1 nodes): `Twilio webhooks require valid signature — unsigned requests fail.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 212`** (1 nodes): `background.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 213`** (1 nodes): `Deserialize from JSON stored in database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 214`** (1 nodes): `index.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 215`** (1 nodes): `KAIROS Dream Log (contradictions and stale refs)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 216`** (1 nodes): `Autonomous Optimization Architect`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 217`** (1 nodes): `Frontend Developer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 218`** (1 nodes): `CMS Developer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 219`** (1 nodes): `Git Workflow Master`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 220`** (1 nodes): `Rapid Prototyper`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 221`** (1 nodes): `Solidity Smart Contract Engineer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 222`** (1 nodes): `Data Engineer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 223`** (1 nodes): `Threat Detection Engineer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 224`** (1 nodes): `Technical Writer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 225`** (1 nodes): `Senior Developer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 226`** (1 nodes): `Filament Optimization Specialist`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 227`** (1 nodes): `Software Architect`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 228`** (1 nodes): `Email Intelligence Engineer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 229`** (1 nodes): `Code Reviewer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 230`** (1 nodes): `AI Engineer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 231`** (1 nodes): `Feishu Integration Developer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 232`** (1 nodes): `Mobile App Builder`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 233`** (1 nodes): `WeChat Mini Program Developer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 234`** (1 nodes): `Security Engineer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 235`** (1 nodes): `Terminal Integration Specialist`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 236`** (1 nodes): `XR Cockpit Interaction Specialist`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 237`** (1 nodes): `XR Interface Architect`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 238`** (1 nodes): `XR Immersive Developer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 239`** (1 nodes): `visionOS Spatial Engineer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 240`** (1 nodes): `macOS Spatial/Metal Engineer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 241`** (1 nodes): `Engineering Agents Category`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 242`** (1 nodes): `Spatial Computing Agents Category`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 243`** (1 nodes): `Shadow Testing / Dark Launching`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 244`** (1 nodes): `Circuit Breaker Pattern`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 245`** (1 nodes): `Medallion Architecture`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 246`** (1 nodes): `Detection-as-Code`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 247`** (1 nodes): `MITRE ATT&CK Framework`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 248`** (1 nodes): `UUPS Upgradeable Proxy Pattern`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 249`** (1 nodes): `Checks-Effects-Interactions Pattern`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 250`** (1 nodes): `WCAG 2.1 AA Compliance`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 251`** (1 nodes): `Core Web Vitals`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 252`** (1 nodes): `STRIDE Threat Modeling`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 253`** (1 nodes): `Zero-Trust Architecture`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 254`** (1 nodes): `Architecture Decision Record (ADR)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 255`** (1 nodes): `Domain-Driven Design — Bounded Context`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 256`** (1 nodes): `Sigma Detection Rules`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 257`** (1 nodes): `OpenZeppelin`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 258`** (1 nodes): `Foundry`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 259`** (1 nodes): `Apache Spark / PySpark`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 260`** (1 nodes): `dbt (data build tool)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 261`** (1 nodes): `Delta Lake`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 262`** (1 nodes): `SwiftTerm`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 263`** (1 nodes): `Apple Metal API`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 264`** (1 nodes): `WebXR Device API`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 265`** (1 nodes): `RealityKit`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 266`** (1 nodes): `Compositor Services (visionOS)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 267`** (1 nodes): `Feishu/Lark Open Platform SDK`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 268`** (1 nodes): `Filament PHP`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 269`** (1 nodes): `Three.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 270`** (1 nodes): `Demo Script — Generic 2026-04-01`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 271`** (1 nodes): `Demo Script — Coffee Shop 2026-03-12`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 272`** (1 nodes): `Help Article: Managing Your Leads`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 273`** (1 nodes): `Help Article: Widget FAQ`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 274`** (1 nodes): `Help Article: How to Embed the Widget`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 275`** (1 nodes): `Help Article: Birthday Automation`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 276`** (1 nodes): `Help Article: Documents & E-Signatures`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 277`** (1 nodes): `Help Article: Setting Up Appointment Booking`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 278`** (1 nodes): `Help Article: Managing Your Sales Pipeline`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 279`** (1 nodes): `Help Article: Understanding Your Analytics Dashboard`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 280`** (1 nodes): `Help Article: Form Presets`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 281`** (1 nodes): `Help Article: How to Configure Your AI Assistant`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 282`** (1 nodes): `Help Article: Service Types for Booking`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 283`** (1 nodes): `Landing Page: Case Study Template`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 284`** (1 nodes): `Landing Page: A/B Test Headlines`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 285`** (1 nodes): `Social Media Posts — LinkedIn & Facebook`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 286`** (1 nodes): `Email: Welcome (Day 0)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 287`** (1 nodes): `Email: Day 7 Check-In`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 288`** (1 nodes): `Email: Day 14 Upgrade Prompt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 289`** (1 nodes): `Lead Scoring`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 290`** (1 nodes): `Widget Appointment Booking`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 291`** (1 nodes): `Birthday Automation`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 292`** (1 nodes): `Chat Flow Builder`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 293`** (1 nodes): `Form Presets`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 294`** (1 nodes): `Documents & E-Signatures`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 295`** (1 nodes): `Sales Pipeline (Kanban)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 296`** (1 nodes): `Analytics Dashboard`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Module 297`** (1 nodes): `Demo Features to Skip (Internal)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ClientRow` connect `Core App & Chat Engine` to `Module 121`, `Module 116`, `Module 52`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Why does `AgentControlCenterResponse` connect `Analytics Dashboard` to `Core App & Chat Engine`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `MockSupabaseTable` (e.g. with `.table()` and `TestVoiceIncoming`) actually correct?**
  _`MockSupabaseTable` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `MockSupabaseClient` (e.g. with `mock_supabase()` and `TestVoiceIncoming`) actually correct?**
  _`MockSupabaseClient` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `MockSupabaseResponse` (e.g. with `.execute()` and `TestVoiceIncoming`) actually correct?**
  _`MockSupabaseResponse` has 38 INFERRED edges - model-reasoned connections that need verification._
- **What connects `SMS endpoints — send SMS from CRM.`, `Send an SMS via Twilio.`, `Lead scoring engine — rule-based 0-100 scoring with engagement, intent, recency,` to the rest of the system?**
  _1033 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Core App & Chat Engine` be split into smaller, more focused modules?**
  _Cohesion score 0.02 - nodes in this community are weakly interconnected._