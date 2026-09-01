#!/usr/bin/env bash
# Run support-tenant Calendar+Gmail M8 live smoke against staging.
# No Cursor Cloud Agent secrets required if .env.staging is populated
# (via m8_pull_railway_staging_env.py or m8_import_railway_vars_json.py).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.staging ]]; then
  echo "STOP: missing .env.staging — run scripts/m8_pull_railway_staging_env.py first" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1091
source .env.staging
set +a

export M8_SMOKE_AUTHORIZED=1
export M8_SMOKE_ENV=staging
export M8_SMOKE_CONFIRM_ENV=staging
export M8_SMOKE_SUITES="${M8_SMOKE_SUITES:-calendar,gmail}"
export M8_SMOKE_CLIENT_ID="${M8_SMOKE_CLIENT_ID:-3ddd9072-ad9f-4214-970d-11386d8c1b4a}"
export M8_SMOKE_ALLOW_EXTERNAL_SEND="${M8_SMOKE_ALLOW_EXTERNAL_SEND:-1}"
export SEND_EMAIL_ENABLED="${SEND_EMAIL_ENABLED:-1}"
export CALENDAR_ACTIONS_ENABLED="${CALENDAR_ACTIONS_ENABLED:-1}"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python3 scripts/m8_live_smoke.py
