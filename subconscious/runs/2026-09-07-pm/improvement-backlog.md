# Improvement Backlog — Run 118 (2026-09-07-pm)

## Active

- **Create `meter-ai-endpoint` skill** — 6-step checklist for the reserve/record/release metering lifecycle. Closes the remediation gap that Step 9L (now live) leaves open. 30–60 min saved per endpoint. HIGH confidence.

## Parking Lot (survived debate but not chosen)

- **os_tool_executions.py god class split** — 783L file, governance mandated "10d+ stable". Actual stability: 4 days (last commit f22ef04 2026-09-03). Revisit run 119 if still 0 commits by 2026-09-13.
- **staging-preflight skill** — 2 preflight patterns in one week, diverging structure. MEDIUM priority. No mandate. Run 120+ candidate.
- **Step 9J token budget diagnosis** — 17/19 Dependabot PRs skipped. Needs diagnostic: which prior nightly step consumes the budget before Step 9J processes all PRs. Fix: move Step 9J earlier or add a per-step budget checkpoint log.

## Rejected This Run

- **Update ai-feature-pattern SKILL.md** — subsumed by the `meter-ai-endpoint` winner. Implement as a bonus action within the same PR (one cross-reference line in the existing skill).

## Questions for Next Run

- Did Step 9L fire on the next nightly? How many violations? How many issues filed vs dedup-skipped?
- Is `meter-ai-endpoint/SKILL.md` approved and merged? If 2nd carry-forward fires: autonomous-executable.
- os_tool_executions.py: 10d+ stable by run 119?
- KB staleness: 12 days as of today — did Step 9G trigger kb-autopopulate.yml?
- Step 9J: which nightly step eats the budget before Step 9J can process all 19 Dependabot PRs?
