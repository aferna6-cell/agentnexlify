# Feature rollout matrix — Agent OS capabilities (2026-08-30)

Distinguish **merged** (code on main), **live-proven** (controlled smoke), and
**enabled** (flag on). Do not flip all capabilities globally at once.

| Flag | Development | Staging | Canary | Production | Current state | Proof completed | Blocker | Rollback |
|------|-------------|---------|--------|------------|---------------|-----------------|---------|----------|
| `RAG_ENABLED` | OK to exercise locally | Candidate: holdout Recall@1≈0.902, refusal 1.0, leaks 0, injection 0; keep `min_score=1.0` | Candidate after staging soak | **OFF** | Merged (#707); migration **198 APPLIED** | Offline + holdout yes; live tenant soak **no** | Owner enable + soak | Set `RAG_ENABLED=0` |
| `SEND_EMAIL_ENABLED` | Optional local with test mailbox | **OFF** until live Gmail procedure | **OFF** | **OFF** | Merged data plane | Offline M6 0/59 unsafe; live send **incomplete** | Controlled Gmail proof (propose→approve→one send→Message-ID→redrive) | Set `SEND_EMAIL_ENABLED=0` |
| `CALENDAR_ACTIONS_ENABLED` | Optional local | **OFF** until Calendar smoke | **OFF** | **OFF** | Merged offline (#709) + data-plane finalize | Offline M8 265/265; live Calendar **blocked on OAuth auth** | Staging Google OAuth + harmless calendar | Set `CALENDAR_ACTIONS_ENABLED=0` |
| `CRM_ACTIONS_ENABLED` | Optional local | **OFF** until CRM smoke | **OFF** | **OFF** | Merged offline (#709) + data-plane finalize | Offline M8; live CRM **needs staging tenant** | Staging lead + cross-tenant negative | Set `CRM_ACTIONS_ENABLED=0` |

## RAG rollout assessment (no retrieval-model change)

1. **Staging:** Yes — eligible with frozen `min_score=1.0`, fast disable, monitor refusal/leak metrics.
2. **Internal/canary tenant:** Yes — after staging looks clean for a soak window.
3. **Broader production:** Not yet — wait for canary soak; keep default OFF.

## Gmail rollout assessment

Do **not** enable globally. Prepare/run existing M6 live Gmail procedure; enable
staging only after exactly-one send + redrive proof.

## Production capabilities now enabled

None of the four flags are enabled in production by default. Owner may enable
staging flags only after the corresponding smoke checklist passes.
