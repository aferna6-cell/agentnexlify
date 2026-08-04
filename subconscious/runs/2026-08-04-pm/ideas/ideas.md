# Ideas — Run 101 (2026-08-04-pm)

5 candidate improvement ideas. Evidence-backed, atomic, not frozen or rejected.

---

### Idea 1: Strengthen Subconscious SKILL.md Dedup Guard with Mandatory Tool-Call Pre-flight

**Evidence:** Morning digest 2026-08-04 Priority 1: "Resolve Step 9G PR duplication — #625 vs #626 both implement KB self-heal. Pick one; close the other." 5 open draft subconscious PRs total (#625, #626, #613, #611, #606). Run 100 winning-concept.md written 2026-07-23; now 12 days later two competing PRs exist and the winner is still unmerged. Existing dedup guard in SKILL.md Phase 8 is prose-only: "BEFORE creating any branch or PR, list open PRs…" — headless sessions don't follow prose instructions reliably.

**Action:** In `.claude/skills/subconscious/SKILL.md` Phase 8 (Commit section), replace the prose dedup guard with a mandatory **STEP 0** block containing explicit tool-call instructions: call `mcp__github__list_pull_requests` (state=open), filter for head branch starting with `subconscious`, if found → fetch that branch, commit artifacts there, push, do NOT open new PR. Only if zero open subconscious PRs found: create new branch + one draft PR.

**Impact:** Ends PR proliferation immediately. Every future headless subconscious run follows a deterministic, tool-call-enforced path instead of guessing. Eliminates the manual cleanup burden (morning digest Priority 1 for the 2nd consecutive digest). Channel proven: SKILL.md edits in autonomous path deliver in 1 cycle (Steps 9B–9F all shipped this way).

**Category:** workflow

---

### Idea 2: Resolve Step 9G PR Competition by Recommending Human Action on #625 vs #626

**Evidence:** `grep -c "Step 9G" .claude/skills/nightly-commit-review/SKILL.md` returns 0. Two open PRs (#625, #626) both implement Step 9G KB self-heal. KB is now 12 days stale (last run 2026-07-23). Step 9G would auto-repair this if in SKILL.md. Morning digest Priority 1.

**Action:** File deterministic recommendation in run artifacts directing human to: (1) review #625 vs #626 diff, (2) merge the one that exactly matches the implementation sketch in `subconscious/runs/2026-07-23/winning-concept.md`, (3) close the other as duplicate. This is a human-action recommendation (merging PRs is beyond autonomous scope), not a self-executing change.

**Impact:** KB staleness repaired. Step 9G active in nightly within hours of merge. Closes morning digest Priority 1.

**Category:** operational

---

### Idea 3: Typed KB Notes Retrieval Audit — Verify Source Filter in /api/chat Path

**Evidence:** Commit `4853c31` (typed KB notes, 2026-08-04 feature) ships `POST /api/v1/kb/{tenant_id}/notes` with `source='note'` in `tenant_kb_documents`. Nightly review confirmed all invariants pass. But: no evidence was checked that the `/api/chat` KB retrieval path returns `source='note'` entries alongside `source='file'` entries. If the retrieval filters by `source='file'` only, typed notes are dark — never served in AI responses.

**Action:** Grep `backend/routers/` and `backend/services/` for KB retrieval calls. Check whether any `source` filter exists on `tenant_kb_documents` queries. If filter found that excludes `source='note'`: file LOW-risk GH issue with exact line references.

**Impact:** Typed notes actually usable in AI chat responses for 3 live tenants. Feature shipped clean but functionally invisible if retrieval is source-gated.

**Category:** code_health

---

### Idea 4: VOYAGE_API_KEY Alert — Step 9J in Nightly SKILL.md

**Evidence:** `knowledge-base/log.md` last entry (2026-07-23): "Embeddings SKIPPED (no credentials/VOYAGE_API_KEY; FTS fallback active)." VOYAGE_API_KEY has been missing for ≥12 days. Semantic search degraded to FTS-only for all 3 live tenants. Typed KB notes (4853c31) will also land without embeddings. This is a silent degradation — no alert fires anywhere.

**Action:** Add Step 9J bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9G (once 9G is merged): parse `knowledge-base/log.md` for "SKIPPED" or "no credentials" string; if found, comment on GH #403 with specific diagnostic: "Step 9J: VOYAGE_API_KEY missing — embeddings skipped, FTS-only fallback active. Add VOYAGE_API_KEY to GH Actions Secrets."

**Impact:** Voyage key absence surfaces in GH within 24h of the next nightly run. Same channel (SKILL.md bash block) proven across Steps 9B–9F.

**Category:** operational

---

### Idea 5: Consolidate Stale Subconscious PRs — Audit and Close Superseded Drafts

**Evidence:** 5 open draft subconscious PRs: #625 (2d, Step 9G), #626 (2d, Step 9G), #613 (4d, Step 9G + Step 9I), #611 (5d, Step 9H GH Actions CI alerter), #606 (7d, feature-docs-trio SKILL.md). Morning digest Priority 3: "Triage stale subconscious drafts — #604, #606, #611, #613 are 4–7 days old. Review each: merge, close, or re-open as GH issue."

**Action:** For each open subconscious PR: read PR body, check if implementation is superseded by a newer approach (e.g., Step 9H was killed in run 100 debate — MCP tenant count too low). Close clearly superseded ones with explanation. Flag PRs whose content is still current for human merge review.

**Impact:** Reduces PR noise from 5 to ≤2. Makes the open PR list actionable instead of overwhelming. Prevents future confusion about which approach to merge.

**Category:** workflow
