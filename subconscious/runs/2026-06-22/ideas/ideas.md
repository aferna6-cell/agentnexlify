# Candidate Ideas — Run 65 (2026-06-22)

**Context:** First free-choice run since 2026-06-15 repricing. Both moratorium_override revenue bugs (GH #292/#293 + GH #308) IMPLEMENTED since run 64. Run 65 mandate is MOOT. 2163 tests passing, 0 failed. check_project_invariants.py passes all 6 checks.

---

### Idea 1: Add plan-name guard Check 7 to check_project_invariants.py (AUTONOMOUS-EXECUTABLE)

**Evidence:** GH #292/#293 fix (`57f2bb4`) landed 2026-06-22 but only after a 6-day production regression — agent_os tenants paying $99.99/mo had NO premium features since the 2026-06-15 repricing. The guard was listed as Bonus B in run 64 winning-concept.md and is explicitly AUTONOMOUS-EXECUTABLE once GH #292/#293 is fixed. check_project_invariants.py already has 6 guards (pre-commit Check 13); this is the 7th. test_plan_gating_new_plans.py now asserts the exact constants we'd guard. Future pricing changes or new plan names will silently omit these sets without a guard.

**Action:** Append a new check to `scripts/check_project_invariants.py`: verify both `"chatbot"` and `"agent_os"` appear in `sms_rate_limiter._UNLIMITED_PLANS` and `api_key_auth._ALLOWED_PLANS`. FAIL if either is missing. ~15 lines Python. Nightly review autonomous execution path confirmed (Check 13 precedent: `bc91e97`).

**Impact:** Prevents next pricing change from silently breaking plan gating for days. From 6-day gap to 0-day gap on plan-name omissions. Every future repricing or new plan is auto-guarded at commit time.

**Category:** code_health

---

### Idea 2: Implement AI-to-Human Handoff v1 (run 4, day 57+, Critical)

**Evidence:** customer-gaps.md lists AI-to-Human Handoff as Critical, all 7 industries affected. `os_outbound_mirror.py` (PR #188, 2026-05-27) handles SMS/email/Facebook outbound — delivery infrastructure is ready. `conversations` table exists. widget_chat.py handles chat flow. Run 38 re-scoped implementation from ~3 days to ~1 day via Agent OS. This has been the oldest pending item since run 4 (2026-04-16, now 57 days). Test suite at 2163 tests — foundation solid.

**Action:** (1) Add `_HANDOFF_TRIGGERS = {"talk to someone", "speak to a human", "real person", "agent please"}` detection in `widget_chat.py`. (2) On match, write to `handoff_requests` table (new migration). (3) Call `os_outbound_mirror.send_sms(owner_phone, message)` and `os_outbound_mirror.send_email(owner_email, subject, body)`. (4) Return handoff acknowledgment to widget.

**Impact:** Resolves #1 customer gap across all 7 industries. Estimated conversion lift: ~10-15% on complex query sessions. Enables upsell from chatbot→agent_os tier (live agent as premium feature).

**Category:** customer_value

---

### Idea 3: Split widget_chat.py god class (1307L) using /god-class-splitter

**Evidence:** `widget_chat.py` is 1307L — larger than email_sequences.py (1143L) which was the target of run 41 and is still pending. New finding this run (not previously tracked in active_directions). god-class-splitter SKILL.md created by run 33 (`e848b87`). 3 clear concerns visible from function names: (a) session management/routing ~300L, (b) lead capture/qualification ~400L, (c) booking/scheduling ~300L. widget_chat.py is the hottest file in the repo — every widget feature touches it. CLAUDE.md Rule 9: >600L → factor first.

**Action:** Invoke `/god-class-splitter` on `backend/routers/widget_chat.py` → split into `widget_chat_session.py` + `widget_chat_leads.py` + `widget_chat_booking.py`. Run post-split-test-repair SKILL.md after.

**Impact:** Reduces blast radius for widget bugs. Enables targeted test coverage for each concern. Unblocks AI-to-Human Handoff (Idea 2) which needs to touch widget_chat.py cleanly.

**Category:** code_health

---

### Idea 4: Fix kb-autopopulate.sh (broken 46+ days, autonomous-candidate)

**Evidence:** `scripts/daily/kb-autopopulate.sh` uses `agent-browser` CLI which is not installed in this environment (confirmed by `fill-instructions-before-guessing.md` pattern — agent-browser hook was the canonical incident). Knowledge base last compiled 2026-05-05 (KB stale 46 days per run 53). KB is the tenant differentiation moat per CLAUDE.md. 114 articles stuck — no new articles auto-added despite active product development. Twice-daily auto-population (6 AM + 6 PM) is a governance promise. Parking lot entry from run 54 (ROI 1.8).

**Action:** Edit `scripts/daily/kb-autopopulate.sh` to: (1) detect when `agent-browser` is unavailable (`which agent-browser 2>/dev/null || true`), (2) fall back to `curl`/native fetch for URL sources, or (3) skip gracefully with a log entry rather than failing silently. If fallback not feasible, add `KB_AUTOPOPULATE_DISABLED=1` env gate with clear log message.

**Impact:** Restores twice-daily KB auto-population. Knowledge base compounds — every day of staleness is a missed article that would improve tenant KB quality and competitive differentiation.

**Category:** operational

---

### Idea 5: Investigate and triage GH #263 (24 pending migrations — CRITICAL)

**Evidence:** GH #263 was filed as CRITICAL 5+ days before run 62, added to parking lot with note "insufficient triage to formulate atomic fix." The issue reports 24 pending migrations — but this could mean (a) genuinely unapplied migrations causing schema drift, or (b) migration tracking table out of sync with actual DB state. Schema changes only via numbered migration files (CLAUDE.md invariant #8). If genuinely pending: critical. If phantom: close the issue and add detection guard.

**Action:** (1) Read GH #263 for exact error output. (2) Cross-reference `migrations/` directory listing vs `schema_migrations` table via Supabase MCP. (3) Determine disposition: genuinely pending migrations vs tracking drift. (4) If tracking drift: document why and close. If genuinely pending: escalate to human with apply commands.

**Impact:** Either closes a phantom CRITICAL issue (reduces alert fatigue) or surfaces a real schema integrity problem before it causes data loss. Either way compounds the governance system.

**Category:** code_health
