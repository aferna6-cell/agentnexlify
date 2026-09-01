# Idea 1 — Step 9L: Nightly Connector Auth Pattern Scan

**Category:** code_health
**Effort:** S
**Autonomous-executable:** YES

## Evidence
- Commit 8a60a59 (2026-08-30): `gmail_connector.py` received 101-addition 401 retry fix
- `backend/services/gmail_connector.py`: only Python connector file with 401 handling, token refresh, retry-once pattern
- `connector_awareness.py` and `connector_registry.py`: no 401 handling confirmed
- Step 9I precedent (run 110): nightly grep-based demo-role sweep → autonomous-executed, validated
- M8 sprint active: new connectors being added at pace; auth gap will recur

## Action
Add Step 9L bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9K.
Grep `backend/services/*_connector.py` for HTTP 401 response handling.
Flag files missing refresh-once retry.
File GH issue with labels `security, ai-ready` if violations found (dedup guard).

## Impact
Prevents next connector auth failure at production scale.
Catches auth gaps before customer-facing incidents.
Leverages nightly routine already running — zero new infrastructure.

## Implementation sketch
```bash
# Step 9L — Connector Auth Pattern Scan
connector_files=$(find backend/services -name "*_connector.py" 2>/dev/null)
missing_401=()
for f in $connector_files; do
  if ! grep -q "401\|refresh\|retry" "$f" 2>/dev/null; then
    missing_401+=("$f")
  fi
done
if [ ${#missing_401[@]} -gt 0 ]; then
  # Log warning + file GH issue (dedup: check for open issue with same title)
  echo "Step 9L: ${#missing_401[@]} connector(s) missing 401 handling: ${missing_401[*]}"
else
  echo "Step 9L: all connectors have 401 handling — PASS"
fi
```

## Verdict
**WINNER** — evidence strong, mechanism proven by 9I precedent, autonomous-executable, zero production risk.
