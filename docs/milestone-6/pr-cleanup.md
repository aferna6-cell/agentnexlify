# Milestone 6 — PR state (#693–#703)

| PR | State | Disposition |
|---|---|---|
| #694 | MERGED | Production — typed Agent OS action foundation |
| #695 | MERGED | Production — Gmail/send contract tests |
| #696 | MERGED | Production — independent validation-v3 |
| #697 | MERGED | Production — L2 idempotency + redaction |
| #699 | MERGED | Production — unknown-send, pre-claim, claim-gated execute |
| #700 | MERGED | Production — Sales-only `send_email`, `SEND_EMAIL_ENABLED` default OFF |
| #693 | OPEN draft | **Reference/research only.** Do not merge wholesale. Useful pieces extracted onto this Milestone 6 branch. |
| #698 | OPEN draft | Measurement experiment (Haiku vs H runner). Superseded as a production candidate by this bakeoff. Keep branch for evidence. |
| #701 | OPEN draft | Measurement experiment (unsafe-action). Research-only. |
| #702 | OPEN draft | Measurement experiment (in-memory send/L2). Research-only. |
| #703 | OPEN draft | Measurement experiment (claim-then-execute FakeGmail). Useful as evidence; production contracts already on main via #695/#699/#700. |

Merged PR descriptions that still say "do not merge" should be read with this
post-merge clarification: those notes applied to the **research** branch, not
to the already-merged slices (#694–#700).
