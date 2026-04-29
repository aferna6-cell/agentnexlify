# Winning Concept — 2026-04-24

## Recommendation
Fix the incorrect byte-identical widget invariant in CLAUDE.md to include all three widget copies
(widget/, frontend/public/widget/, landing-page-v2/widget/), and create a CI sync-check script
that fails if any copy drifts.

## Why This, Why Now
CLAUDE.md Critical Invariant #4 states: "Widget JS byte-identical in `widget/` AND
`frontend/public/widget/`." But there is a THIRD active copy: `landing-page-v2/widget/`. The
developer's own 2026-04-21 evening routine flagged "Codify widget 3-way sync check as skill —
widget/ + frontend/public/widget/ + landing-page-v2/widget/ touched twice today." Every session
since then has executed the sync protocol for only 2 copies, silently leaving the landing page
widget potentially out of sync. The landing page drives customer demos and inbound signups — a
drifted widget on that page breaks live demos. S-effort, zero infrastructure dependencies,
prevents silent customer-facing regressions.

## Implementation Sketch
1. **Update CLAUDE.md** — Change Critical Invariant #4 from:
   > "Widget JS byte-identical in `widget/` AND `frontend/public/widget/`"
   to:
   > "Widget JS byte-identical in `widget/`, `frontend/public/widget/`, AND
   > `landing-page-v2/widget/` — all three must stay in sync."

2. **Create `scripts/check-widget-sync.sh`:**
   ```bash
   #!/usr/bin/env bash
   # Checks all 3 widget copies are byte-identical. Skip missing copies gracefully.
   set -e
   W1="widget/agentnexlify-widget.js"
   W2="frontend/public/widget/agentnexlify-widget.js"
   W3="landing-page-v2/widget/agentnexlify-widget.js"
   FAIL=0
   for pair in "$W1 $W2" "$W1 $W3" "$W2 $W3"; do
     A="${pair%% *}"
     B="${pair##* }"
     [ -f "$A" ] && [ -f "$B" ] || continue
     if ! diff -q "$A" "$B" >/dev/null 2>&1; then
       echo "MISMATCH: $A vs $B"
       FAIL=1
     fi
   done
   [ "$FAIL" -eq 0 ] && echo "Widget sync: OK (copies identical)" || exit 1
   ```

3. **Wire into pre-push hook** — Add after existing checks:
   ```bash
   # Widget 3-copy sync guard
   if bash scripts/check-widget-sync.sh 2>/dev/null; then
     :
   else
     echo "BLOCKED: widget copies out of sync. Copy widget/agentnexlify-widget.js to all 3 paths."
     exit 1
   fi
   ```

4. **Verify** — Run `bash scripts/check-widget-sync.sh` to confirm all copies currently match.

5. **Document** — One line in `docs/dev-knowledge/schema-log.md`:
   `2026-04-24: widget 3-copy sync guard added — CLAUDE.md updated, scripts/check-widget-sync.sh created.`

## What This Replaces
No previous active direction displaced. Diversifies run 7 away from pure pre-commit hook additions
(run 6) toward documentation correctness + lightweight tooling.

## Confidence
HIGH — Evidence triple-backed: (1) developer's own 2026-04-21 evening note explicitly flagging
the 3rd copy, (2) CLAUDE.md invariant text visibly wrong (only 2 paths listed), (3) S-effort
pure-bash implementation, zero external dependencies. Debate: survived all 4 challenges. Ideas 2
and 3 weakened into parking lot.
