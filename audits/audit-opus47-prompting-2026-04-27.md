# Audit — Opus 4.7 Prompting Hygiene

**Date:** 2026-04-27
**Scope:** `.claude/agents/`, `.claude/skills/`, `backend/services/`
**Source rule:** `.claude/rules/opus-4-7-prompting.md` §Audit checklist
**Auditor:** Opus 4.7 (this session)
**Fixes:** Out of scope per `.claude/rules/daily-skills.md` §"Don't fix and audit in the same session"

---

## Findings (ranked: impact × effort)

### CRITICAL — none
No security/invariant breakage. All findings are token-efficiency / prompt-quality.

---

### HIGH 1 — RETRACTED — `grill-me/SKILL.md` already migrated

**Original audit claim:** Line 56 still enforces drip-feed.

**Re-verification (2026-04-27, this session):** False positive. grill-me is at v1.1.0 with full batch-mode loop at lines 46-56. Step 3 says "Batch 5-8 numbered questions for ONE branch in ONE message". Line 56 ("Never drip one question at a time. Never mix branches in one batch") is the GUARD against drip-feed, not the cause.

**Source of stale audit:** `opus-4-7-prompting.md §1` and §"Cross-refs" both still listed grill-me as "needs batch-mode rewrite" — those were stale post-v1.1.0. Fixed in same session per `fill-instructions-before-guessing.md` rule (instruction-first fix before downstream work).

**Net:** No HIGH-priority items remain. Top fix targets are now MEDIUM 1 and MEDIUM 2.

---

### MEDIUM 1 — Negative-rule bloat in agents (139 occurrences / 47 files)

**Scope:** `.claude/agents/*.md`
**Pattern:** "never", "don't", "do not", "avoid"

**Issue:** Per `opus-4-7-prompting.md §2`, 4.7 treats negative rules as token cost without behavior lock-in; positive examples anchor output shape better. With 139 negative-rule lines across 47 agents loaded into context (lazily, per-invoke), token waste compounds across every Agent spawn.

**Fix shape:**
- Per agent, audit each "never/don't/avoid" line
- KEEP if it's a security invariant, legal/compliance, or schema discipline (e.g. `client_id not tenant_id`)
- FLIP to positive example otherwise: "never X" → "like this: <good example>"

**Estimated salvage:** ~70% of 139 are flippable (security invariants stay). Net: ~95 lines flipped, ~5-10 tokens saved per agent invocation × N invocations/day.

**Effort:** L (47 files, ~3 min/file = ~2.5 hours focused work)
**Impact:** MEDIUM — long tail benefit; not load-bearing but compounds

---

### MEDIUM 2 — Negative-rule bloat in skills (291 occurrences / 76 files)

**Scope:** `.claude/skills/*/SKILL.md`
**Pattern:** "never", "don't", "do not", "avoid"

**Issue:** Same as MEDIUM 1, larger surface. Skills are loaded on trigger match — high-traffic skills (`caveman-mode`, `karpathy-guidelines`, `compound-engineering`, daily-skills gates) have outsized impact.

**Fix shape:**
- Prioritize by skill traffic: caveman-mode, karpathy-guidelines, grill-me, write-prd, prd-to-issues, tdd-workflow, compound-engineering FIRST
- Long-tail skills (verticals, partner tooling) DEFER

**Effort:** XL (76 files, top-10 in ~1 hour, full sweep ~4 hours)
**Impact:** MEDIUM — top-10 skills cover ~80% of session loads

---

### LOW 1 — Progress scaffolding (clean)

**Pattern:** "summarize every", "status update", "explain your plan"
**Result:** Only `opus-4-7-prompting.md` (the rule file itself) matches.

**No action.** Project skills already lean on 4.7's native self-narration. Confirms `daily-skills.md` and `compound-engineering` were already authored without scaffolding bloat.

---

### LOW 2 — Legacy `budget_tokens` (clean)

**Pattern:** `budget_tokens` in `backend/services/`
**Result:** 0 files.

**No action.** Already migrated to `thinking: {type: adaptive}` + `output_config.effort` per `advisor-consult.md §"Opus 4.7 specifics"`. Confirms 2026-04-20 migration was complete.

---

## Token-savings estimate

If MEDIUM 1 + MEDIUM 2 fully executed:
- ~430 negative-rule lines × ~5-8 tokens per line = ~2,500-3,400 tokens of agent/skill context bloat
- Roughly 70% flippable = ~1,750-2,400 tokens reclaimed across loaded agents/skills per session
- Effect compounds: cleaner context → better instruction adherence → fewer correction turns

Not enormous in raw count, but agent/skill prompts are loaded on every relevant invocation — multiplied across daily sessions, the win is real.

---

## Recommended fix sequence (separate sessions)

~~Session A~~ — RETRACTED. grill-me already at v1.1.0 batch-mode. Stale `opus-4-7-prompting.md` references fixed inline this session.

1. **Session B (M effort, MEDIUM impact):** Top-10 skills negative-rule audit. caveman-mode, karpathy-guidelines, daily-skills gates. ~1 hour.
2. **Session C (L effort, MEDIUM impact):** Top-10 agents (backend-dev, frontend-dev, schema-guardian, opus-advisor, sonnet-executor, code-reviewer, qa-tester, vertical-checker, widget-specialist, devops). ~1 hour.
3. **Session D (XL, low priority):** Long-tail skills + agents. Defer; revisit only if context-pressure becomes visible in `claude-usage-monitor`.

---

## Cross-refs
- `.claude/rules/opus-4-7-prompting.md` — source audit checklist
- `.claude/rules/daily-skills.md` §"Don't fix and audit in same session"
- `.claude/skills/grill-me/SKILL.md` — top fix target
- `.claude/rules/usage-observability.md` — measure before/after via `claude-usage`

## Verification
Verified: 5-grep audit checklist from `opus-4-7-prompting.md` executed in prior turn — PASS (5/5 queries returned results, 2 clean / 3 with findings).
