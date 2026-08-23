# Debate Log — Subconscious Run #109
## Date: 2026-08-23-pm
## Top 3 ideas debated: Idea 1, Idea 2, Idea 3

---

## Idea 1: Step 9J — Dependabot auto-merge with major-version safety gate

### Challenge
"Run 108's winning-concept specified the merge heuristic as 'CI green + no review request + no blocking labels.' It did NOT include a major-version gate. Adding a gate changes the approved spec. Also, are we sure the PR title format is consistent enough for regex parsing? If the title format varies, we'd silently skip PRs we should catch, or worse, merge major bumps we should skip."

### Defend
"The run 108 winning-concept was an approved recommendation, not a locked implementation spec. The 19 open PRs include react 18→19 (#586/#591/#593) and stripe v11→v15 (#598) — both major-version bumps with known breaking changes. Merging these automatically without human review would be a significant risk. The 'CI green' check doesn't validate semantic compatibility, only build success.

On title format: GitHub Dependabot PRs follow a consistent format: 'Bump {package} from {old} to {new}'. The version tokens are always present and well-formed. A regex like `from \d+\.\d+\.` → capture leading digit; `to \d+\.\d+\.` → capture leading digit; if major version digit increases, skip. This is robust across the 19 real PRs in scope.

The safety refinement is additive: it makes Step 9J safer, not narrower in a harmful way. It correctly targets what run 108 intended (patch/minor security updates) while excluding risky major bumps. The governance escalation_condition doesn't require byte-identical implementation — it requires Step 9J to be implemented. This IS Step 9J, with a necessary safety gate."

### Verdict
**SURVIVES — WINNER**
Mandate-triggered (carry-forward escalation at run 109), channel proven (5 prior Steps same path), safety refinement addresses real 19-PR risk. Major-version gate is conservative and correct. Will be implemented directly this run (1st carry-forward = autonomous-executable per governance).

---

## Idea 2: Step 9K — Stale subconscious PR closer

### Challenge
"Step 9K is a valid idea but why this run? Step 9J is already the mandate. Adding 9K is scope expansion beyond what's been governance-approved for autonomous execution. Also, the 14-day threshold is arbitrary — what if a PR is 15 days old but has relevant context? Closing it loses that context."

### Defend
"The 14-day threshold is conservative and targets PRs with 0 code commits (pure state/docs artifacts). Context loss is minimal — the actual work is in governance.json + memory.jsonl, not the PR body. The 6-PR count exceeds the mandate threshold (≥3 triggers Step 9K candidacy). This is a real operational issue: PR #626 and #674 both claim 'run 109' causing confusion.

However, the challenge is correct on sequencing. Step 9J is the primary carry-forward. Step 9K has not yet hit its own carry-forward threshold (this is the first run where mandate conditions are met, not the carry-forward run). The nightly SKILL.md can only absorb so much in one commit — adding two Steps in one run risks validation errors and complicates rollback."

### Verdict
**WEAKENED — parking lot for run 110**
Valid idea, mandate conditions now met (6 PRs ≥3 threshold). Will be run 110's primary candidate. This run: Step 9J only. Parking lot entry added to improvement-backlog.md.

---

## Idea 3: GH #669 middleware-level block_demo_role guard

### Challenge
"97/97 routers is a systemic security gap. Subconscious has filed issues but no PR has materialized (AUTOPILOT_GH_TOKEN expired). Why isn't subconscious taking direct action? The route-security-guard-audit SKILL.md exists. The fix pattern is documented in the GH #669 issue body. This seems like M-effort but the middleware approach makes it S-effort — one file, one change."

### Defend
"The middleware approach is architecturally non-trivial. FastAPI middleware runs before dependency injection — it can read request headers and path, but the block_demo_role dependency currently works via FastAPI's Depends() system which has access to the full auth context (tenant role from JWT). Middleware that replicates this logic needs to: (1) parse and validate JWT, (2) extract tenant role, (3) check if role == 'demo', (4) match path against allowed mutations for demo tenants. This duplicates auth logic — a code smell and a maintenance burden.

The correct architectural fix is either: (a) individual Depends() per router (97 files, M-effort), or (b) a FastAPI APIRouter with the dependency baked in, requiring routers to subclass it (refactor). Neither is autonomous-executable in this run — both touch 97 files or core auth architecture. The subconscious channel handles SKILL.md edits, not M-effort architectural changes. GH #399 (token expiry) is the real blocker for issue-to-pr-loop to process GH #669."

### Verdict
**KILLED — wrong channel for this run**
Correct security priority. Wrong implementation channel (subconscious handles SKILL.md edits; this needs human-approval session + issue-to-pr-loop or direct engineering). Will remain in open-blockers section. Unblocked by GH #399 resolution (AUTOPILOT_GH_TOKEN rotation).
