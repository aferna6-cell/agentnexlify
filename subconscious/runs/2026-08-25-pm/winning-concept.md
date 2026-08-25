# Winning Concept — Run 111 (2026-08-25-pm)

## Winner: Pre-commit block_demo_role detection hook

**Category:** security  
**Effort:** M  
**Confidence:** HIGH  
**Status:** PENDING HUMAN APPROVAL  
**Channel:** human-approve-implement (not autonomous-executable — requires new script + hook wiring)

---

## Why This Won

10acf83 (revenue sprint, 46 files, today) added `backend/routers/partners.py` WITHOUT `Depends(block_demo_role)`. `backend/routers/billing_addons.py` in the SAME commit HAS it correctly (lines 22/35). This is an accidental omission, not a deliberate bypass — both files were committed in one sprint.

Step 9I (nightly detection) is reactive: partners.py will be caught at the 2026-08-26 2:37 AM nightly, ~22h after the endpoint was live. A pre-commit hook catches it at zero lag.

GH #669 tracks 97 accumulated violations — the systemic lesson is that detection alone doesn't prevent recurrence. Prevention at commit time is the compounding fix.

---

## Implementation Spec

### File 1: `scripts/claude-hooks/check-router-guards.sh`

```bash
#!/bin/bash
# Pre-commit: warn when staged router files have mutating endpoints but lack block_demo_role
# WARNING-only — does not block commits. Shift-left signal.

VIOLATIONS=()

for file in $(git diff --cached --name-only --diff-filter=ACM | grep "^backend/routers/.*\.py$"); do
    # Skip known auth/webhook/public exceptions
    basename=$(basename "$file")
    case "$basename" in
        auth.py|auth_google.py|auth_password_reset.py) continue ;;
        stripe_webhooks.py|twilio_webhooks.py|resend_webhooks.py) continue ;;
        widget_chat.py|widget_lead.py|widget_config.py) continue ;;
    esac

    # Check if file has mutating endpoints
    if grep -qE "@router\.(post|put|delete|patch)" "$file" 2>/dev/null; then
        # Check if block_demo_role is used
        if ! grep -q "block_demo_role" "$file" 2>/dev/null; then
            VIOLATIONS+=("$file")
        fi
    fi
done

if [ ${#VIOLATIONS[@]} -gt 0 ]; then
    echo ""
    echo "⚠  block_demo_role WARNING (pre-commit)"
    echo "   These staged router files have mutating endpoints but lack block_demo_role:"
    for v in "${VIOLATIONS[@]}"; do
        echo "   - $v"
    done
    echo ""
    echo "   Fix pattern:"
    echo "     from backend.dependencies import block_demo_role"
    echo "     from fastapi import Depends"
    echo "     @router.post('/endpoint')"
    echo "     async def create_thing(..., _: None = Depends(block_demo_role)):"
    echo ""
    echo "   See GH #669 for class-wide context."
    echo "   This is a WARNING — commit is NOT blocked. Add guard before merging to main."
    echo ""
fi
```

### File 2: Update `scripts/install-hooks.sh`

Add to the pre-commit hook installation section (after the existing `__future__` check):

```bash
# Block_demo_role router guard warning
bash scripts/claude-hooks/check-router-guards.sh
```

### Note on placement

The hook is WARNING-only (`exit 0` always). It does not block the commit. Rationale: blocking would create friction for emergency hotfixes and would be bypassable with `--no-verify` anyway. The goal is immediate developer feedback, not hard enforcement. Hard enforcement stays with Step 9I + code review.

---

## Bonus A: Annual Plan Guard Audit (XS, do alongside)

Check that `ai_usage_guard.py` PLAN_BASELINE_TOKENS correctly classifies annual plan subscribers. 10acf83 added annual prepay billing. Verify:

```bash
grep -n "PLAN_BASELINE_TOKENS\|plan_name\|agent_os\|chatbot" backend/services/ai_usage_guard.py | head -30
```

If annual plan names (e.g. `agent_os_annual`, `chatbot_annual`) are not mapped, annual subscribers get free-tier token limits on day 1. File GH issue if gap found.

---

## Expected Impact

- **Immediate:** partners.py omission visible at commit time on next sprint touching that file
- **Compounding:** every new router file checked automatically at commit — no new GH #669-class violations
- **CVE window:** 12-36h nightly lag → 0h for committed files
- **Human cost:** 2-4h to implement script + hook wiring

---

## Run 112 Mandate

1. Pre-commit hook implemented? Check `scripts/claude-hooks/check-router-guards.sh` exists and `scripts/install-hooks.sh` calls it.
2. Step 9K fired in first nightly after approval: check `grep 'Step 9K:' ops/routines/logs/nightly-commit-review-*.md`. How many PRs closed? How many escalated?
3. Annual guard audit: `grep -n "PLAN_BASELINE" backend/services/ai_usage_guard.py | grep -i annual` — does it exist?
4. partners.py: Step 9I filed GH issue for it? Check `grep 'partners.py' ops/routines/logs/nightly-commit-review-2026-08-26.md`.
5. GH #669 PR #653 (block_demo_role middleware): still open? Any review?
6. Step 9D GH Actions dark: 37+ days — escalation issue filed? (Parking lot candidate if not.)
