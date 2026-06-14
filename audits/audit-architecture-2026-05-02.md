# Architecture Health Report — 2026-05-02

Source: `python3 .claude/skills/improve-architecture/scripts/audit.py` + manual passes 4 + 6.

## CRITICAL (fix before next deploy)

### God classes (>1000 lines)
- [ ] `backend/routers/auth.py` (1506 lines) | Pass 1 | Effort: L — split into auth, password, session, token modules
- [ ] `backend/tests/test_managed_agents.py` (1374 lines) | Pass 1 | Effort: M — split by feature (lead-qual, appt-book, etc.)
- [ ] `backend/routers/widget_chat.py` (1271 lines) | Pass 1 | Effort: L — extract handlers + helpers (already has widget_chat_helpers.py at 776)
- [ ] `backend/routers/email_sequences.py` (1255 lines) | Pass 1 | Effort: L — split routes / engine / triggers
- [ ] `backend/routers/invoices.py` (1211 lines) | Pass 1 | Effort: L — split CRUD / webhooks / PDF
- [ ] `backend/routers/onboarding.py` (1199 lines) | Pass 1 | Effort: L — also has 3 N+1 insert loops (lines 486, 507, 798, 924)
- [ ] `backend/routers/calls.py` (1175 lines) | Pass 1 | Effort: L
- [ ] `backend/routers/leads.py` (1158 lines) | Pass 1 | Effort: L
- [ ] `tests/test_automation_engine.py` (1106 lines) | Pass 1 | Effort: M
- [ ] `backend/routers/booking_page.py` (1065 lines) | Pass 1 | Effort: L

### Layer violations
- [ ] `backend/routers/conversation_inbox.py:217,244` | Pass 2 | Effort: S — comments reference frontend session_id resolution; verify this is intentional pattern, not dependency leak

## HIGH (fix this sprint)

### God classes (600–1000 lines, 22 files)
- [ ] `backend/main.py` (909) — split route registration block (lines 746–813) into `backend/routes_register.py`
- [ ] `backend/models/schemas.py` (999) — split into per-domain schema modules
- [ ] `backend/routers/billing.py` (907)
- [ ] `backend/routers/forms.py` (860)
- [ ] `backend/routers/bids.py` (858)
- [ ] `backend/routers/widget_lead_helpers.py` (833)
- [ ] `backend/routers/client_portal.py` (830)
- [ ] `backend/services/automation/scheduled_jobs_ext.py` (792)
- [ ] `backend/routers/widget_chat_helpers.py` (776)
- [ ] `backend/routers/marketing_campaigns.py` (721)
- [ ] `backend/routers/admin_analytics.py` (690)
- [ ] `backend/routers/sequences.py` (679)
- [ ] `backend/routers/appointments.py` (648)
- [ ] `backend/routers/analytics/dashboard.py` (628)
- [ ] `backend/services/booking.py` (622)
- [ ] `backend/routers/pipeline.py` (619)
- [ ] `backend/routers/social_media.py` (618)
- [ ] `backend/routers/channels_facebook.py` (607)
- [ ] `backend/services/branding_service.py` (606)
- [ ] `backend/routers/analytics/control_center.py` (606)
- [ ] `backend/services/local_seo_handlers.py` (886)
- [ ] `backend/services/automation/rule_engine.py` (875)

### Sync calls in async services
- [ ] `backend/services/llm_runtime.py:316` | Pass 6 | Effort: S — `time.sleep` in retry loop; use `asyncio.sleep` if caller is async
- [ ] `backend/services/managed_agents.py:145,187,503,526` | Pass 6 | Effort: S — same retry pattern; confirm callers are sync; if any call from async path → asyncio.sleep

### N+1 query candidates
- [ ] `backend/routers/onboarding.py:486` | Pass 6 | Effort: M — single insert in loop; batch via `.insert(rows_list)`
- [ ] `backend/routers/leads.py:714,866` | Pass 6 | Effort: M — per-lead update inside loop; batch via RPC or upsert

## MEDIUM (tech debt backlog)

### Dead imports (23 files)
- [ ] `backend/main.py:891` — `HTTPException`
- [ ] `backend/services/automation_engine.py:2` — `get_service_supabase`
- [ ] `backend/services/branding_service.py:17` — `get_service_supabase`
- [ ] `backend/routers/conversations.py:7,8` — `get_current_tenant`, `branding_service`
- [ ] `backend/routers/integrations.py:99` — `build`
- [ ] `backend/routers/widget_chat.py:134` — `agent_sdk_client`
- [ ] `backend/routers/appointments.py:559` — `Response`
- [ ] `backend/routers/widget_config.py:29` — `_get_current_tenant`
- [ ] `backend/routers/auth.py:330` — `INDUSTRY_FAQS`
- [ ] `backend/routers/faq.py:8,9` — `get_current_tenant`, `branding_service`
- [ ] `backend/services/automation/rule_engine.py:12` — `increment_sms_count`
- [ ] `backend/services/automation/scheduled_jobs/_common.py:4-24` (8 unused imports)
- [ ] `backend/routers/analytics/__init__.py:5,6` — `get_service_supabase`, `_cache`

Single batched fix: 1 commit, ~10 min via dead-code-sweep skill.

## LOW

_None._

## False positives ruled out (Pass 4 verified clean)
- `backend/routers/reviews.py` uses `tenant_id` — legitimate. Migration `019_reviews.sql` defines `tenant_id` on the `reviews` table. Schema-discipline rule applies only to `leads` + `conversations`.
- `backend/routers/widget_lead.py` mixes `tenant_id` (function param) + `client_id` (DB column on leads). Comment at line 119 explicitly notes the rule. Not a violation.

## Stats
- Files >600 lines: **34** (10 critical, 24 high)
- Layer violations: 2 (low confidence — likely false positive, comment-only)
- Dead-import candidates: 23
- Schema drift risks: 0 (after verification)
- N+1 candidates: 5
- Sync-in-async: 5

**Total actionable: 67 items**

## Next steps
1. Dead imports → `dead-code-sweep` skill, single PR (~10 min)
2. main.py split (line 746–813 routes block) → 1 PR, separate concern
3. onboarding.py → highest-priority god-class because also has N+1 (compound win)
4. auth.py split → highest-risk because security-critical; do under `/ultrareview` gate

Do NOT batch the god-class splits. Each is its own PR with its own tests. Per `user-rules.md` Rule 8: no half migrations.

## Cross-refs
- `.claude/rules/user-rules.md` Rule 9 (god class threshold)
- `.claude/skills/compound-engineering/SKILL.md` (split workflow)
- `.claude/skills/dead-code-sweep/SKILL.md` (dead-import batch)
