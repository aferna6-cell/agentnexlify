# Milestone 6 PR hygiene (#693–#703)

| PR | Title | State | Classification |
|---|---|---|---|
| #694 | Action foundation (slice A) | **MERGED** | Production. Post-merge clarification: this is the shipped action layer. Earlier "do not merge" draft language is obsolete. |
| #695 | B-prep Gmail contracts | **MERGED** | Production tests. |
| #696 | Independent validation-v3 | **MERGED** | Production dataset. Now used as the bakeoff **selection** set. |
| #697 | L2 idempotency + input redaction | **MERGED** | Production. |
| #699 | Unknown send, pre-claim validation, claim-gated run | **MERGED** | Production. |
| #700 | Sales-only `send_email` behind default-off flag | **MERGED** | Production. Flag stays off. Post-merge: the PR body still says "Do not merge. Draft." — that is stale; the work is on main. |
| #693 | Action layer + harness + pipeline + ML (wholesale) | OPEN draft | **Reference / research only.** Do not merge wholesale. Useful pieces extracted onto this milestone branch. |
| #698 | Haiku vs H measurement runner | OPEN draft | Superseded as a production path. Keep as measurement research. |
| #701 | Haiku vs H unsafe-action measurement | OPEN draft | Superseded by the production safety detectors + orchestrated harness. |
| #702 | In-memory Haiku vs H send/L2 | OPEN draft | Research. FakeGmailPort ideas reused; runner not merged. |
| #703 | send/L2 claim-then-execute | OPEN draft | Research successor to #702. Claim-then-execute protocol informed the harness; not merged wholesale. |

Branches and result artifacts on #693 / #698–#703 are retained. Nothing useful is deleted.
