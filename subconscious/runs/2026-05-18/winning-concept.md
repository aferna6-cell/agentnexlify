# Winning Concept — 2026-05-18 (Run 23)

## Recommendation

Create a single branch `moratorium-exit-sprint` containing all 4 pending S-effort items as
one draft PR — converting four separate approval decisions into one, reducing pending from
9 to 5 in the fewest possible decision steps.

---

## Why This, Why Now

**Approval friction is the bottleneck, not knowledge or time.** Every pending S-effort item
has a pre-written implementation sketch. Total execution time is ~50 minutes. Every previous
run communicated these items — the human knows about them. What changes this run: framing
them as a single bundle with one approval decision instead of four sequential ones. Approval
friction drops 4×.

**This is the first run where a sprint PR is the PRIMARY winner** (not a bonus or footnote).
Runs 15–22 mentioned sprint items as secondary recommendations. This run makes the consolidation
the sole recommendation, maximizing prominence and minimizing the chance it gets lost in other
details.

**check_project_invariants.py passes all 6 checks right now** (verified live this session).
Zero blockers for any of the 4 items: pre-commit addition is stdlib-only, widget sync script
is a new file, SKILL.md addition is purely additive, CI eval file is self-contained. No
migrations, no auth changes, no breaking code changes.

**Run 20 governance mandate fires this run regardless.** max_pending_approvals reduces from
3 to 2. The governance pressure is structural — this run must apply the mandate. Pairing the
mandate with the highest-impact pending-reduction action maximizes the run's leverage.

---

## Implementation Sketch

**Estimated time: ~50 minutes total. One branch. One draft PR.**

### Step 0: Create branch

```bash
git checkout -b moratorium-exit-sprint
```

### Step 1: Wire check_project_invariants.py (Item A — ~5 min)

Edit `scripts/hooks/pre-commit`. After the Check 9 (JS silent catch) block — around line 220
(ends with `echo -e "${GREEN}OK${NC}"`), add:

```bash
# Check 10: Project invariants (client_id, status, areas_of_interest naming)
echo -n "Check 10: Project invariants... "
python3 scripts/check_project_invariants.py || exit 1
echo -e "${GREEN}OK${NC}"
```

Verify: `python3 scripts/check_project_invariants.py` → all PASS, exit 0.

Commit: `chore: add Check 10 — wire check_project_invariants.py into pre-commit (run 8)`

### Step 2: Widget 3-Copy Sync Guard (Item B — ~15 min)

Create `scripts/check-widget-sync.sh`:

```bash
#!/bin/bash
# Check that all 3 widget JS copies are byte-identical.
# Paths: widget/, frontend/public/widget/, landing-page-v2/widget/
set -e

WIDGET_CANONICAL="widget/agentnexlify-widget.js"
WIDGET_COPY1="frontend/public/widget/agentnexlify-widget.js"
WIDGET_COPY2="landing-page-v2/widget/agentnexlify-widget.js"

FAIL=0
if ! diff -q "$WIDGET_CANONICAL" "$WIDGET_COPY1" > /dev/null 2>&1; then
    echo "FAIL: $WIDGET_CANONICAL and $WIDGET_COPY1 differ"
    FAIL=1
fi
if [ -f "$WIDGET_COPY2" ] && ! diff -q "$WIDGET_CANONICAL" "$WIDGET_COPY2" > /dev/null 2>&1; then
    echo "FAIL: $WIDGET_CANONICAL and $WIDGET_COPY2 differ"
    FAIL=1
fi
if [ "$FAIL" -eq 0 ]; then
    echo "OK: all widget copies are byte-identical"
fi
exit $FAIL
```

```bash
chmod +x scripts/check-widget-sync.sh
```

Wire into `scripts/hooks/pre-push` — add call after existing checks:

```bash
# Widget sync check
echo -n "Widget sync check... "
bash scripts/check-widget-sync.sh || { echo "BLOCKED: widget copies differ"; exit 1; }
```

Fix CLAUDE.md Invariant #4: change `"**Widget JS byte-identical** in \`widget/\` AND \`frontend/public/widget/\`"` to include all 3 paths:
`"**Widget JS byte-identical** in \`widget/\`, \`frontend/public/widget/\`, AND \`landing-page-v2/widget/\`"`

Verify: `bash scripts/check-widget-sync.sh` → OK.

Commit: `chore: add widget 3-copy sync guard script + pre-push hook + fix CLAUDE.md Invariant #4 (run 7)`

### Step 3: Moratorium Escalation Protocol in SKILL.md (Item C — ~10 min)

Edit `.claude/skills/nightly-commit-review/SKILL.md`. Add a new section after the existing
final step (step 9 or wherever the steps end):

```markdown
## Moratorium Escalation Protocol

When `subconscious/state/governance.json` shows `moratorium_config.moratorium_active: true`
AND `moratorium_config.oldest_pending` > 14 days:

**Step 9A (automated):** Post a comment on the oldest pending GH issue linking to the winning
concept:
1. Read `governance.json` → find `active_directions[0]` (most recent pending winner)
2. Find the relevant GH issue number (from `active_directions[*].note`)
3. Post: "Moratorium active — this item has been pending for N days. See implementation
   sketch: `subconscious/runs/{date}/winning-concept.md`"
4. Log: append entry to `ops/routines/logs/nightly-commit-review-{date}.md` under
   "Moratorium Escalation"

Trigger condition: `moratorium_active: true` AND `oldest_pending_days > 14`.
Frequency: once per nightly run (not every run if already escalated today).
```

Commit: `docs: encode Moratorium Escalation Protocol in nightly-commit-review SKILL.md (runs 18/19)`

### Step 4: Lead Qualifier Eval CI Workflow (Item D — ~20 min)

Create `.github/workflows/lead-qualifier-eval.yml`:

```yaml
name: Lead Qualifier Golden Eval

on:
  schedule:
    - cron: '0 8 * * 1'  # Monday 8am UTC
  pull_request:
    paths:
      - 'backend/services/lead_qualifier*.py'
      - 'backend/tests/evals/**'
  workflow_dispatch:

jobs:
  lead-qualifier-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run golden eval harness
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
        run: |
          cd backend
          python -m pytest tests/evals/test_lead_qualifier_golden.py -v --tb=short
```

Commit: `ci: add lead-qualifier golden eval workflow — Monday cron + PR trigger (run 14, closes #110)`

### Step 5: Open Draft PR

```bash
git push -u origin moratorium-exit-sprint
```

Open draft PR: "Moratorium Exit Sprint — 4 S-effort guards in one PR"

Body:
```
Implements 4 pending subconscious recommendations as a single sprint:

- **Check 10**: wire check_project_invariants.py into pre-commit (run 8, 23 days)
- **Widget sync guard**: scripts/check-widget-sync.sh + pre-push hook + CLAUDE.md fix (run 7, 24 days)
- **Moratorium Escalation Protocol**: encode in nightly-commit-review SKILL.md (runs 18/19, 2 days)
- **CI eval workflow**: lead-qualifier golden eval on Monday cron + PR trigger (run 14, 13 days)

Pending drops 9→5. Closest to moratorium exit in 23 runs.
All items are purely additive — no production code modified, all reversible.

Implementation sketches: `subconscious/runs/2026-05-18/winning-concept.md`
```

---

## What This Replaces

Run 22's winner ("Wire check_project_invariants.py into pre-commit") is subsumed as Item A of
this sprint. No conflict — same action, broader bundle.

Run 21's winner (AI-to-Human Handoff GH Issue) remains valid and is NOT addressed by this PR.
Parking lot with pre-written sketch at `subconscious/runs/2026-05-17/winning-concept.md`.

---

## What Comes After

After sprint PR merged (pending 8→4):

**Remaining pending items (4):**

| Run | Item | Effort |
|-----|------|--------|
| 4 | AI-to-Human Handoff v1 (feature build) | M 1.5-2d |
| 20 | Governance threshold reduction (applied in run 23 governance.json) | Applied this run |
| 21 | AI-to-Human Handoff GH Issue | S ~15 min |
| 18 (partial) | Automated Moratorium Escalation Hook — SKILL.md now updated (Item C) | Partially complete |

Note: Run 20 (governance milestone) and Run 18 (SKILL.md) are addressed by this sprint + governance
mandate. Effective pending after all resolutions: 4→2 (run 4 feature + run 21 GH issue). If run 21
also done: pending 4→1 → moratorium exits (new threshold: 2).

**Run 24 candidates (after moratorium exits):**
- AI-to-Human Handoff v1 feature build (M-effort, CRITICAL, oldest item)
- Zapier API key plan_status enforcement (ROI 2.5, GH #107, security)
- Email sequences N+1 fix (ROI 2.3, GH #112)
- Investigate autopilot-issue-loop status (parking lot, free-choice run)

---

## Confidence

**HIGH** — All 4 items have pre-written sketches, verified zero blockers, and are purely additive.
The sprint PR framing is novel (first time as primary winner). Only uncertainty: whether the
human acts on it. Debate outcome: Idea 1 SURVIVES (3 rounds), Idea 5 WEAKENED → parking lot,
Idea 4 WEAKENED → parking lot.
