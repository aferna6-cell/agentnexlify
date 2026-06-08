# Candidate Ideas — Run 2026-06-08-pm (Run 52)

## Evidence Summary (run 52)

**Key observations (last 3 days):**
- Agent OS Phase 3 shipped fast: PRs #205 (auth hardening), #207 (v2 dashboard), #208 (routing chip + slot extraction). 30+ agents in registry.
- **NEW security finding:** GH #206 filed by nightly 2026-06-07 (HIGH) — `===` string comparison on `X-Agent-Token` in `agent-service/src/auth.ts` is a timing attack vector. PR #209 open 1 day.
- **Widget hijack bug (2287f6b, 2026-06-07):** `os_inbound_bridge` `_DEFAULT_CONFIG.widget_enabled` was `True` — Agent OS was hijacking the public chat widget by default. Fixed to `False` (opt-in).
- **Two security-adjacent issues in agent-service in 7 days.** agent-service has zero pre-commit guards. Python backend has 11.
- Items A+B still pending_autonomous — PR #200 (3d open, SKILL.md scope extension) not merged, blocking autonomous nightly execution.
- AMOUNT_TO_PLAN still missing 15000/25000 (GH #181, 16 days). PR #183 (15d draft) not merged.
- KB 34 days stale — VOYAGE_API_KEY missing in cron env.
- email_sequences.py still 1255L (run 41 winner, day 8+ unimplemented).
- Nightly review clean last 3 runs (0 bugs filed) — Agent OS quality holding.

---

### Idea 1: Merge PR #200 — unblock Items A+B autonomous chain tonight
**Evidence:** PR open 3 days (labeled "subconscious run 49"). Items A+B both marked AUTONOMOUS-EXECUTABLE but blocked on this SKILL.md merge. Morning digest #2 priority. Tonight's nightly (2:37 AM) can auto-execute both items if PR on main.
**Action:** Human merges PR #200 → Items A+B execute in tonight's nightly
**Impact:** 2 moratorium items auto-close (Check 10 wire + widget sync guard). pending_autonomous drops to 0 pending items by morning.
**Category:** workflow

### Idea 2: Merge PR #209 — close timing attack in agent-service auth (HIGH security)
**Evidence:** GH #206 filed by nightly review 2026-06-07 (HIGH). `agent-service/src/auth.ts` uses `===` for `X-Agent-Token` comparison — standard timing side-channel. PR #209 open 1 day, fix is `timingSafeEqual(a, b)` swap. Morning digest #1 priority.
**Action:** Human merges PR #209
**Impact:** Closes HIGH security vulnerability in agent-service auth before Agent OS is fully customer-facing.
**Category:** code_health

### Idea 3: Add Check 12 — agent-service timing-safe guard to pre-commit (AUTONOMOUS-EXECUTABLE)
**Evidence:** GH #206 timing attack (auth.ts `===` on token) + 2287f6b opt-in/opt-out default bug = 2 security-adjacent incidents in 7 days on agent-service. Python backend: 11 pre-commit guards preventing bug recurrence (Checks 1-11). agent-service TypeScript layer: 0 guards. agent-service growing fast (30+ agents). Commit 061582c confirmed nightly can autonomously add 12-line bash blocks to pre-commit (Check 11 pattern).
**Action:** Add ~12-line bash block to `scripts/hooks/pre-commit` as Check 12 (WARNING mode): scan `agent-service/src/**/*.ts` for `===` comparison patterns on variables named `token`, `key`, `secret`, `header` without `timingSafeEqual` context. Label AUTONOMOUS-EXECUTABLE.
**Impact:** First systemic pre-commit security guard for TypeScript agent-service layer. Catches timing-attack class at commit time (vs current 12-24h nightly review delay). Compounds across all future agent additions. AUTONOMOUS-EXECUTABLE by nightly review (exact same class as Check 11).
**Category:** code_health

### Idea 4: Agent OS booking agent eval harness
**Evidence:** 30+ agents shipped, 0 Agent OS evals. Slot extraction just added PR #208. lead-qualifier-eval.yml CI pattern proven (run 14 winner, now active CI). PR #207 adds v2 dashboard rendering — Agent OS is becoming customer-visible. Next code change to extract-slot.ts has no regression guard.
**Action:** Create `backend/tests/evals/test_booking_agent_golden.py` + 10 golden cases (slot extraction happy path, day-only, time-only, no-match, plural day names). Wire into lead-qualifier-eval.yml CI.
**Impact:** First regression guard for Agent OS agents. Prevents extract-slot regressions as booking agent evolves.
**Category:** agent_performance

### Idea 5: Fix KB cron VOYAGE_API_KEY gap
**Evidence:** Morning digest flag: "KB stale 34 days. Embeddings blocked (no VOYAGE_API_KEY in cron)." kb-autopopulate.sh runs but skips embeddings silently. pgvector semantic search (/kb-query) degraded. Competitive intelligence compounding lag.
**Action:** Add graceful fallback to `scripts/daily/kb-autopopulate.sh`: if `VOYAGE_API_KEY` unset, print WARNING + skip embedding step (don't fail). Separately: add `VOYAGE_API_KEY` to Railway cron env.
**Impact:** Unblocks KB text-article compilation (immediate). Restores embeddings when key added. Closes 34-day self-harm gap in competitive intelligence.
**Category:** operational
