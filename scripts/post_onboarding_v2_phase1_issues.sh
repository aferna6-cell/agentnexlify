#!/usr/bin/env bash
# Post phase 1 GH issues for onboarding-v2 (issues 1-4 from plans/onboarding-v2_issues.md)
# Run after `gh auth login`. Idempotent only at the script level — re-running creates duplicates.
set -euo pipefail

REPO="aferna6-cell/agentnexlify"

ensure_label() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --color "$color" --description "$desc" --repo "$REPO" 2>/dev/null || true
}

echo "==> Ensuring labels exist"
ensure_label "migration"          "0E8A16" "Database migration work"
ensure_label "backend"            "1D76DB" "Backend / FastAPI"
ensure_label "security"           "B60205" "Security-critical change"
ensure_label "priority:critical"  "B60205" "Critical priority"
ensure_label "priority:high"      "D93F0B" "High priority"
ensure_label "priority:medium"    "FBCA04" "Medium priority"
ensure_label "onboarding-v2"      "5319E7" "Onboarding v2 epic"

echo "==> Issue 1: migrations 113-116"
ISSUE_1=$(gh issue create --repo "$REPO" \
  --title "Add migrations 113-116 (widget_configs extras, vertical_presets, integrations encryption, welcome_email_attempts)" \
  --label "migration,backend,priority:high,onboarding-v2" \
  --body "$(cat <<'EOF'
## User story
As a developer, I need the schema landed before any v2 service can run so that all writes have valid storage.

## Acceptance criteria
- `migrations/113_widget_configs_v2_extras.sql` adds `vertical_preset`, `last_health_check_at`, `last_health_check_status` to `widget_configs`
- `migrations/114_vertical_presets.sql` creates table + RLS + 6-row seed from `config/vertical_defaults.yaml`
- `migrations/115_integrations_encrypt_access_token.sql` enables pgcrypto + adds `access_token_enc BYTEA`, `refresh_token_enc BYTEA`
- `migrations/116_welcome_email_attempts.sql` creates table + indexes + RLS
- All 4 apply via `mcp__supabase__apply_migration` against staging without error
- `docs/dev-knowledge/schema-log.md` updated with rationale + numbering reconciliation

## Files expected to change
- `migrations/113_widget_configs_v2_extras.sql` (new)
- `migrations/114_vertical_presets.sql` (new)
- `migrations/115_integrations_encrypt_access_token.sql` (new)
- `migrations/116_welcome_email_attempts.sql` (new)
- `config/vertical_defaults.yaml` (new)
- `docs/dev-knowledge/schema-log.md` (modify)

## Blocking
- Blocked by: none
- Blocks: Issues 2, 3, 4, 5, 6, 7

Source: `plans/onboarding-v2_issues.md` Issue 1
EOF
)")
echo "  -> $ISSUE_1"
NUM_1=$(echo "$ISSUE_1" | grep -oE '/issues/[0-9]+' | grep -oE '[0-9]+')

echo "==> Issue 2: integration_key_vault"
ISSUE_2=$(gh issue create --repo "$REPO" \
  --title "Build integration_key_vault with 100% test coverage" \
  --label "backend,security,priority:critical,onboarding-v2" \
  --body "$(cat <<EOF
## User story
As a tenant, I need my Stripe/Twilio/Resend keys encrypted at rest so a DB leak doesn't expose them.

## Acceptance criteria
- \`backend/services/integration_key_vault.py\` exposes \`encrypt(key) -> bytes\`, \`decrypt(ct) -> str\`, \`mask(key) -> str\`
- Uses \`INTEGRATIONS_ENC_KEY\` env var (AES-256 via pgcrypto pgp_sym_encrypt or app-side cryptography.fernet — pick in PR description)
- Module raises at import time if \`INTEGRATIONS_ENC_KEY\` missing (fail-fast)
- \`backend/tests/test_integration_key_vault.py\` covers: round-trip, wrong-key fail, malformed ciphertext fail, NULL handling, mask helper, key version metadata
- \`pytest --cov=backend.services.integration_key_vault --cov-fail-under=100\` passes
- No \`from __future__ import annotations\`

## Files expected to change
- \`backend/services/integration_key_vault.py\` (new)
- \`backend/tests/test_integration_key_vault.py\` (new)

## Blocking
- Blocked by: #${NUM_1}
- Blocks: Issue 8

Source: \`plans/onboarding-v2_issues.md\` Issue 2
EOF
)")
echo "  -> $ISSUE_2"
NUM_2=$(echo "$ISSUE_2" | grep -oE '/issues/[0-9]+' | grep -oE '[0-9]+')

echo "==> Issue 3: vertical_preset_loader"
ISSUE_3=$(gh issue create --repo "$REPO" \
  --title "Build vertical_preset_loader (DB-first, YAML fallback)" \
  --label "backend,priority:medium,onboarding-v2" \
  --body "$(cat <<EOF
## User story
As a wizard service, I need to fetch per-vertical defaults so I can pre-seed the wizard 70% filled.

## Acceptance criteria
- \`backend/services/vertical_preset_loader.py::load(vertical) -> dict\` returns \`{display_name, default_services, default_faqs, default_hours, avg_ticket_amount, avg_hours_saved_per_lead}\`
- DB read from \`vertical_presets\` first, falls back to \`config/vertical_defaults.yaml\` if row missing
- 6 verticals: plumbing, hvac, cleaning, power_washing, landscaping, electrical
- Test: DB hit, YAML fallback, unknown vertical returns None
- Hook into \`backend/services/industry_packs/__init__.py\` so packs ALSO seed KB (not just automations)

## Files expected to change
- \`backend/services/vertical_preset_loader.py\` (new)
- \`backend/services/industry_packs/__init__.py\` (modify)
- \`backend/tests/test_vertical_preset_loader.py\` (new)
- \`config/vertical_defaults.yaml\` (new — same file as Issue 1, share author)

## Blocking
- Blocked by: #${NUM_1}
- Blocks: Issue 5

Source: \`plans/onboarding-v2_issues.md\` Issue 3
EOF
)")
echo "  -> $ISSUE_3"
NUM_3=$(echo "$ISSUE_3" | grep -oE '/issues/[0-9]+' | grep -oE '[0-9]+')

echo "==> Issue 4: welcome_email_retrier"
ISSUE_4=$(gh issue create --repo "$REPO" \
  --title "Build welcome_email_retrier with exponential backoff" \
  --label "backend,priority:high,onboarding-v2" \
  --body "$(cat <<EOF
## User story
As Maria, if my welcome email fails once, the system should retry quietly and tell me only if all retries failed.

## Acceptance criteria
- \`backend/services/welcome_email_retrier.py\` schedules 3 retries: +30s, +2min, +10min after initial send fails
- Writes one row per attempt to \`welcome_email_attempts\` (status pending/sent/failed/skipped)
- 4th-attempt failure flips a banner-trigger flag readable by frontend
- Hook into \`backend/services/automation/scheduled_jobs.py\` for execution
- Hook into \`backend/services/email_sender.py\` to record initial attempt
- Test simulates time-travel; covers cap-3, idempotency, 429-retry-later
- No \`from __future__ import annotations\`

## Files expected to change
- \`backend/services/welcome_email_retrier.py\` (new)
- \`backend/services/automation/scheduled_jobs.py\` (modify)
- \`backend/services/email_sender.py\` (modify)
- \`backend/tests/test_welcome_email_retrier.py\` (new)

## Blocking
- Blocked by: #${NUM_1}
- Blocks: Issue 13 (banner UI)

Source: \`plans/onboarding-v2_issues.md\` Issue 4
EOF
)")
echo "  -> $ISSUE_4"

echo
echo "Done. 4 issues posted."
echo "Issues 5-21 still in plans/onboarding-v2_issues.md — post when phase 1 lands."
