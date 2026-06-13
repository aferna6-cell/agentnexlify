# PR #212 Merge-Readiness Assessment — 2026-06-13

Branch: `claude/gap-3-research-worker-87IXF` (draft PR #212). Assessment only —
no merge executed. Produced for goal "complete items 1–5", item 2.

## CORRECTION (later same day): histories are UNRELATED — no clean rebase/merge

A merge attempt revealed `git merge-base origin/main <branch>` = **NO COMMON
ANCESTOR**. `origin/main` was squashed to a fresh root on 2026-06-10 (`#231` is now
the root); gap-3 branched off the *old* main (~05-27, two roots 05-23/05-27) and was
never rebased. They share file **content** (why the tree-merge shows few conflicts)
but **disjoint history**. Consequences:

- `git merge` refuses ("unrelated histories"); a rebase would replay 92 commits
  against a non-ancestor — both impractical.
- `--allow-unrelated-histories` 3-way-merges every shared file against an empty base
  → spurious conflicts across the whole tree. Do not.
- **Correct path: cherry-pick / re-apply #212's features individually off current
  main**, as reviewed slices — not a single rebase. Start with self-contained pieces
  (`wordpress-plugin/` is a standalone PHP plugin, zero backend coupling). Features
  whose migrations pair with shared-file code (qualifier rubrics, integration-health)
  come as full CI-gated slices. The migration-collision analysis below still applies.

## Verdict: NOT mergeable as-is. Unrelated histories + 3 migration collisions.

| Check | Result |
|---|---|
| `git merge-tree origin/main` textual conflicts | **0** (auto-merges cleanly) |
| `origin/main` ancestor of branch? | No — real 3-way merge |
| Branch behind main | **50 commits** (last branch work 2026-06-09) |
| Branch ahead of main | **92 non-merge commits** |
| Migration-number collisions | **3 (BLOCKER)** |
| CI green? | Cannot confirm — PR Validation workflow disabled (see #185 / Item 3A) |

## The blocker: duplicate migration numbers

The branch was cut when main was at migration ~132, then both sides independently
used 133/134/135. A clean text-merge keeps **both** files per number → the
migration runner gets ambiguous ordering and `pr-check.yml`'s migration-numbering
step fails on duplicates.

| # | main (keep) | gap-3 (renumber) |
|---|---|---|
| 133 | `133_os_graph_memory.sql` | `133_pending_automations.sql` → `146_` |
| 134 | `134_pricing_ab_events.sql` | `134_qualifier_settings.sql` → `147_` |
| 135 | `135_referral_columns.sql` | `135_tenant_stripe_connect.sql` → `148_` |

Main's highest migration is **145**, so renumber gap-3's three to **146/147/148**.
Grep the branch for any code referencing the old numbers/filenames before renaming.

## What the 92 commits deliver (launch-readiness, issues #213–#217)

- WordPress plugin — `wordpress-plugin/agentnexlify/*` (one-click install, #214)
- Integration-health / "is my widget live?" probe (#215)
- Per-vertical qualifier rubrics + owner controls — `134_qualifier_settings` (#216, the moat)
- Stripe Connect scaffold (inert, flag-off) — `135_tenant_stripe_connect` (#217)
- `pending_automations` table — `133_pending_automations`
- Activity-log parity (#213)
- Pre-launch security: lead IDOR fixes, signed email tracking pixel, widget cost guard, PII-log hardening

## Semantic items to verify during the rebase (text-merge won't flag these)

1. **os_worker test deletions.** The branch deletes `tests/test_os_mvp_e2e.py` +
   `test_os_worker_*` (Python OS workers superseded by the `agent-service/` TS
   engine). Confirm main's own OS cutover already removed/relocated these so the
   merge isn't silently dropping live coverage.
2. **Overlap with the June 10–12 sprint.** Integration-health and activity-parity
   themes also appear in merged sprint PRs (#232–#254). Diff to confirm gap-3's
   versions aren't duplicating or regressing what already landed.
3. **billing.py / .env.example / requirements.txt** also changed on this
   `youthful-pasteur` branch (items 1/3/4). Sequence so the #181 billing fix and
   cryptography pin aren't clobbered.

## Recommended path (do NOT wholesale-merge the stale branch)

1. Branch `gap-3-rebase` off **current main**.
2. Cherry-pick / rebase the 92 commits; renumber the 3 migrations to 146/147/148
   and update `docs/dev-knowledge/schema-log.md`.
3. Drop any commit already superseded by the sprint (item 2 above).
4. Restore CI first (Item 3A — account-level GHA infra) so the suite + migration
   check actually gate the merge.
5. `/ultrareview` — surface is billing + security + 3 migrations.
6. Open a fresh PR; retire #212.

## Effort
M–L. The renumber is mechanical; the risk is the semantic overlap with the sprint.
Single largest stranded body of launch work — worth landing, but only after CI is
back so it's gated, not merged blind.
