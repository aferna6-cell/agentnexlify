# Debate Log — 2026-04-20

Top 3 ideas ranked by impact: Idea 1 (migration guard), Idea 2 (widget split), Idea 3 (spec validation).
Idea 5 (QA triage) is urgency-now but not systemic. Idea 4 (KB seed) compounds but lower urgency.

---

## Idea 1: Migration Duplicate Number Pre-commit Guard

### Challenge

**C1: Is the evidence strong enough?**
The duplicates (005 + 007) are in historical migrations — files that existed before the sequential
naming rule was established. They can't be renumbered without breaking Supabase replay. The pre-commit
guard only prevents FUTURE duplicates (≥106). Is there actual evidence that future migrations will
collide? Only 107 migrations so far — numbering has been clean post-106.

**C2: Highest leverage right now?**
Two pending-approval recommendations from prior runs haven't been implemented. The JS silent-catch
guard (run 3) is functionally similar — extend pre-commit hook — and is sitting idle. If that one
isn't being implemented, why would this one be different?

**C3: What could go wrong?**
Filename-based grep is naive. A contributor naming a file `migrations/106_add_leads.sql` and another
`migrations/106_add_indexes.sql` simultaneously on different branches would both pass pre-commit
independently but still collide on merge. The guard prevents sequential error, not merge collision.

**C4: Similarity to active direction?**
Run 3 active direction = JS silent catch guard (also pre-commit extension). Not identical concern
but same implementation pattern. Risk of "third pre-commit extension that hasn't been acted on."

### Defend

**D1:** Historical duplicates are documented as untouchable. The guard explicitly targets ≥106. The
audit's exact wording: "Enforce strict sequential check for numbers ≥106." The risk isn't that
007 collides again — it's that a fast-moving codebase adding 5+ migrations/week hits 200 migrations
and someone writes 142 twice. Compounding codebases create compounding errors.

**D2:** Previous runs not being implemented is the approval-gate working as designed. The subconscious
recommends; human approves or rejects. That 2+ recommendations are stacked doesn't mean new ones
shouldn't be generated — it means the recommendation quality should stay high to earn approval.

**D3:** The merge-collision scenario is real but edge-case. The pre-commit guard catches the most common
failure mode: developer creating a file locally with an already-used number. Merge collisions are
caught by CI diff checks (already in place). This guard adds a local early-warning.

**D4:** Run 3's JS catch guard is a WARNING pattern. This is a FAIL/BLOCK pattern — harder to ignore.
Different behavioral signal.

### Verdict: SURVIVES

Evidence triple-backed: audit HIGH, CLAUDE.md Rule 8, audit's explicit fix proposal. S-effort, zero
infrastructure, permanent. Distinction from run 3: FAIL block vs WARNING nudge — higher enforcement
weight.

---

## Idea 2: widget_helpers.py Phase 1 — Extract Lead Capture

### Challenge

**C1: Is evidence strong enough?**
"3 bugs in 7 days" comes from the parking lot entry added in run 3 (2026-04-11). That's 9 days ago
now. Have those 3 bugs been fixed? The recent commits don't show new widget_helpers bugs — they show
widget_helpers growing (business-type personalization commit `ad88397` added 37 lines). Evidence is
slightly stale on the 3-bug count.

**C2: Highest-leverage vs. other god classes?**
SettingsPage.jsx is 2,262 lines (bigger). ConversationsPage.jsx is 2,039 lines. Why widget_helpers
over those? The audit ranks them all as HIGH. widget_helpers is backend; the others are frontend.
Backend god classes have higher blast radius (API stability, tenant isolation).

**C3: What could go wrong?**
Extraction requires updating 4 import sites: `widget_chat.py`, `widget_lead.py`, `widget_config.py`,
`twilio_webhooks.py`. Widget JS must remain byte-identical between `widget/` and
`frontend/public/widget/`. Any Python import break cascades to production widget. The byte-identical
rule applies to the JS not the Python, but an import error in the Python kills all chat sessions.

**C4: Effort assessment?**
Audit says Effort M for the full split. Phase 1 only (lead helpers) is probably S-M. But "probably"
is uncertainty. The implementation sketch requires reading 1,635 lines to identify which functions
belong in which module — non-trivial before writing a single line.

### Defend

**D1:** Stale bug count (9 days) is acceptable evidence. The fundamental issue — 1,635L with 4+ import
sites — hasn't changed. `ad88397` added 37 more lines AFTER the audit (commit Apr 17). The trend
is growth, not shrinkage.

**D2:** widget_helpers is the highest-traffic file (4 import sites, 3 of which are live API paths).
SettingsPage.jsx at 2,262L is large but a single-page UI component. widget_helpers bugs hit every
chat session on every tenant.

**D3:** Import update risk is the real objection. But the extraction is pure Python module organization
— no logic changes. Tests in `test_widget_api.py` and `test_lead_enrichment.py` would catch any
import break before commit.

### Verdict: WEAKENED

Right idea, but the import-chain risk + effort-uncertainty makes this L-effort in practice, not S-M.
The audit said Effort L for the full split. Phase 1 alone saves one-third of that. But the subconscious
recommendation should be something a developer can execute in <4 hours with high confidence. Phase 1
extract of widget_helpers is 4-8 hours with risk. Better candidate: park this, recommend in a
widget-specific sprint where the developer has the file fully in context.

Parking lot addition: "widget_helpers.py Phase 1 Extract — park until a widget sprint. Import chain
risk too high for standalone atomic recommendation."

---

## Idea 3: Spec-to-Implementation Symbol Validation Gate

### Challenge

**C1: Evidence strong enough?**
Two bugs from spec drift on April 15. But both were in the same PR (lead-parser-replacement Phase 2).
Is this a pattern or a one-off from one underspecified PR? The spec was written before the implementation
existed — a rare ordering for this project.

**C2: Highest leverage?**
Updating a skill file is voluntary enforcement. Unless there's a hook or CI step, developers
(including Claude) can skip the skill entirely. bug-patterns.md ALREADY says "MUST run
python -c ..." — if that instruction in bug-patterns.md wasn't followed, will a skill update be?

**C3: What could go wrong?**
Spec validation via `python -c` only works for Python import symbols. It doesn't validate SQL
column names, Pydantic field names, or schema deviations. Partial solution creates false confidence.

**C4: Similar to existing rule?**
CLAUDE.md Rule 7 says "Never research code before reading it" and Rule 1-3 address `client_id`/`status`/`areas_of_interest` column discipline. Schema-guard skill already handles pre-migration validation.
Feature-build skill is the right place for this, but the skill needs HOOK enforcement, not just
documentation.

### Defend

**D1:** Two bugs in one PR from spec drift is still systemic — it means the spec authoring process
has no validation gate. If it happened once, it can happen again on the next PR that uses a spec.
Lead-parser-replacement was the most complex spec-driven feature this project has done.

**D2:** Skill update has partial value even without hook enforcement. When Claude reads the skill
before building a feature, it follows the pre-build checks. The skill IS invoked on non-trivial
features (daily-skills.md, TDD-workflow). Adding the step to the skill means it runs in those
sessions even without a hook.

**D3:** Partial solution objection is valid. Python import validation misses SQL column validation.
But bug-patterns.md already covers the SQL case ("grep migrations"). The skill update would link
to both checks, covering both failure modes.

### Verdict: WEAKENED

Right diagnosis but the mechanism (skill update) is weaker than hook enforcement. Risk: another
doc that doesn't get read. The real fix is a pre-build assertion step in the TDD-workflow or
feature-build SKILL.md that actually runs the checks, not just documents them. 

Better path: add this to the parking lot as "Spec Symbol Validation — needs hook enforcement,
not just skill doc update. Revisit with pre-build hook in TDD-workflow."

---

## Synthesis

| Idea | Verdict | Next |
|------|---------|------|
| 1. Migration Duplicate Guard | SURVIVES → WINNER | Implement |
| 2. widget_helpers.py Phase 1 | WEAKENED | Parking lot (widget sprint) |
| 3. Spec Symbol Validation | WEAKENED | Parking lot (needs hook enforcement) |
| 4. Small Business SaaS KB Seed | Not debated | Parking lot (good but lower urgency) |
| 5. QA Triage Sprint | Not debated | Already in current-tasks P1 — not a subconscious recommendation |

**Winner: Idea 1 — Migration Duplicate Number Pre-commit Guard**

Distinct from run 3's JS catch guard: this is a FAIL block (not a WARNING), targets a different
file class (SQL migrations), and addresses an explicit audit HIGH finding. The two prior guards
(Python bare-except → WARNING, JS silent-catch → WARNING) leave a gap: migration numbering
violations have no automated enforcement at all. This fills it.
