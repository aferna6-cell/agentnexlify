# M8 Formal Completion Evidence — 2026-09-02

## Verdict

**M8 COMPLETE** on staging SHA `962da79b97a2e7d0dc766ca32615957e85a8e7ca` (PR #748 branch `cursor/m8-input-preservation-a2c9`).

## Live proof (canonical synthetic tenant)

- Tenant: `7451537b-a694-4c31-83b0-1b804df3d757`
- Artifact: `audits/artifacts/m8-live-smoke-20260902T155302Z.json`
- Suites: Calendar, Gmail, Agent OS E2E, CRM, Isolation, RAG — all PASS
- Exit codes: all 0
- Failures: 0

## Support-tenant precursor (OAuth + product path)

- Tenant: `3ddd9072-ad9f-4214-970d-11386d8c1b4a`
- Gmail-only: `m8-live-smoke-20260902T142008Z.json` PASS
- Calendar+Gmail: `m8-live-smoke-20260902T142104Z.json` PASS

## Local regression gates (same SHA)

| Gate | Result |
|------|--------|
| `npm run eval:actions:gate` | UNSAFE ACTIONS: 0 |
| `npm run eval:calendar-crm:gate` | 265/265 pass |
| `npm run eval:crm-decision-path:gate` | 14/14 pass |

## Fixes required for completion

1. `#748` input preservation — data-plane success no longer wipes parked `send_email` input
2. OAuth state TTL 10m → 60m — stops Calendar callback `400 Invalid or expired state` during 2FA

## Follow-ups (post-M8)

1. Merge #748 to `main`
2. Merge/finalize #747 (brace-expansion) and restore green PR Validation
3. Branch protection / #669 before expanding M9 autonomy
