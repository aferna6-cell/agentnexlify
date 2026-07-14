# Idea 2 — connector_awareness.py Cross-Tenant Isolation Test

## Category
code_health

## Effort
XS (test file only, ~20 min)

## Evidence
- commit 45401ec (2026-07-11): `connector_awareness.py` shipped — 208L service, 370 tests
- commit 7a9047f (2026-07-11, SAME DAY): bug fix — connect prompt fired for dashboard threads because `source='chat'` threads were not filtered out
- Pattern: 370 tests cover behavior (does prompt fire correctly?) but NOT isolation (does it ONLY fire for the correct tenant?)
- connector_awareness sends tenant-specific connector context to Claude prompts; Tenant A seeing Tenant B's connector data = trust breach
- Run 53 pattern: os_action_dispatch.py had same isolation test gap → caught by subconscious → nightly implemented test → test caught real regression before production

## Action
Write `backend/tests/test_connector_awareness_isolation.py`:
1. Create two mock tenants with distinct client_ids (A and B)
2. Seed Tenant A with connector records, Tenant B with different records
3. Call `connector_awareness.build_connector_prompt(client_id=A_id)`
4. Assert: result contains no reference to Tenant B's connector data
5. Repeat for Tenant B → assert no Tenant A data

## Expected Impact
- Catches cross-tenant data leakage in AI connector prompts before it reaches production
- Validates that `7a9047f`'s fix extended correctly to client_id filtering
- Provides regression protection for future connector_awareness changes
- AUTONOMOUS-EXECUTABLE by nightly-commit-review (pure test file)

## Risk
Zero. Test file only. No behavior changes. No schema changes. No production code modified.

## Autonomy
Fully AUTONOMOUS-EXECUTABLE. Nightly-commit-review can implement without human approval. Test file = additive + reversible.
