# Debate Log — 2026-06-12-pm (Run 57)

Top 3 by impact: Idea 1 (CI enforcement), Idea 2 (em-dash fix), Idea 5 (scope extension).

---

## Idea 1: Add `from __future__` CI check to pr-check.yml

### Round 1 — Challenge
**Is the evidence strong enough?**
Check 2 is FAIL-mode in pre-commit. It's been there since run 56 was recommended. Yet
push_subscriptions.py landed with the violation. The evidence of bypass is direct: pre-commit
reads `$STAGED_FILES` which is empty when committing via GitHub PR merge or Claude agent commits.
Evidence is unambiguous.

**Is this the highest-leverage thing?**
8 files infected. 4→8 in 24h. If the rate continues, every new router or service file gets
infected. CI check stops it system-wide. No workaround path exists once CI enforces it.

**What could go wrong?**
CI check added with wrong scope could have false positives (e.g., catching test fixtures or
migration stubs). Risk: low — `from __future__ import annotations` in backend Python files
has zero legitimate use cases in FastAPI (CLAUDE.md Critical Invariant #5).

**Has something similar been tried?**
57 runs, all 12 pre-commit checks added. Zero CI quality checks added (beyond eval harness which
is advisory). This is the first time CI-level enforcement is proposed. Not a repeat.

**Too similar to active direction?**
Run 56 winner is Check 13 (pre-commit). This is CI enforcement — complementary, not conflicting.
Two-layer defense: pre-commit for local dev, CI for all paths. Not a repeat proposal.

### Round 1 — Defend
Pre-commit hooks require installation (`bash scripts/install-hooks.sh`). This repo's commits
come from:
1. Interactive Claude agent sessions in remote containers (fresh clone, no hooks installed)
2. GitHub PR squash merges (hooks don't run server-side)
3. Nightly review autonomous commits (hooks not installed in nightly env)

CI runs on every PR regardless of commit source. Adding a grep step to pr-check.yml is identical
to how lead-qualifier-eval.yml was created (AUTONOMOUS-EXECUTABLE, run 47, nightly 42992fa). That
was a NEW .github/workflows/ file. This is adding a STEP to an existing file — simpler.

The `from __future__` check is zero-ambiguity: `grep -rL ""` on backend/ Python files, fail if
any match. No false positives in current codebase (only legacy test fixtures could trigger it, but
those wouldn't be in backend/).

### Verdict: **SURVIVES**

---

## Idea 2: Fix 8 JSX em-dash violations (AUTONOMOUS-EXECUTABLE)

### Round 1 — Challenge
**Is this the highest-leverage thing to do right now?**
Em-dash fix only clears ONE of THREE invariant failures. Even if em-dashes are fixed, check_project_invariants
still exits 1 (from __future__ check + third failure). Item A (Check 10) remains blocked. The
chain only completes when ALL 3 failures clear. Em-dash-only fix = partial progress but not
unblocking.

**What could go wrong?**
Nothing — 1-char substitution in UI strings. Zero logic risk. Em-dash has 100% autonomous
success rate (nightly 8db33df).

**Is this better than the winning idea?**
No. CI enforcement (Idea 1) is systemic prevention. Em-dash fix is tactical cleanup. Idea 2
doesn't prevent future em-dash violations (no guard added). Idea 1 prevents future from __future__
violations permanently.

**Has this been tried?**
Yes — run 49 winner (8db33df implemented 5 fixes). Pattern recurs with every PR. Em-dash is a
recurring cleanup, not a one-time fix. The real fix would be a CI em-dash guard (not proposed
here).

### Round 1 — Defend
The em-dash fix IS valuable — it's one of the invariant failures and it's 100% autonomous.
But it can't be the WINNER because it doesn't stop recurrence and doesn't unblock the Item A
chain on its own. Valid as Bonus Action alongside the winner.

### Verdict: **WEAKENED** — demote to Bonus Action. Valid, autonomous, zero risk. Execute alongside winner.

---

## Idea 5: Add Python line deletion to nightly autonomous scope (meta)

### Round 1 — Challenge
**Is this the highest-leverage thing?**
No — Idea 1 (CI enforcement) prevents violations at the source. Idea 5 only cleans them up
after landing. Fixing the gate > fixing the leak.

**What could go wrong?**
Meta-loop risk: nightly scope has been extended 4+ times (runs 40/43/47/50). Each extension
compounds scope complexity. Nightly executing Python file edits (line deletions) is higher risk
than SKILL.md creation or JSX string subs — it modifies logic files. A wrong deletion (wrong
line number, wrong file) could break imports or behavior.

**Has something similar been tried?**
Nightly scope extended for: SKILL.md creation (runs 40/43), pre-commit bash additions (runs 43/50),
CI YAML creation (run 47). Python file line deletion NOT tried. Run 55 explicitly attempted
AUTONOMOUS-EXECUTABLE Python edit and nightly d12bd21 did NOT execute it — the gap is real.

**Is there a better mechanism?**
Yes — Idea 1 (CI enforcement) is systemic prevention, making cleanup unnecessary. After CI blocks
new violations, only the current 8 need manual cleanup (5 min, human).

### Round 1 — Defend
The self-healing loop is elegant — once in scope, future infections auto-clear. But "once in scope"
requires yet another meta-SKILL.md edit (the 5th+ scope extension). And Idea 1 makes it
unnecessary by stopping infections at the gate.

### Round 2 — Final check
Even if Idea 5 were implemented, it would still need a trigger: how does the nightly know which
files to clean? It would need to parse check_project_invariants output or scan all backend/*.py.
That's more complex than the current scope extensions (which had explicit file paths in the
winning-concept.md). Idea 1 is simpler and more effective.

### Verdict: **KILLED** — addressed by better mechanism (CI enforcement). Meta-loop adds complexity
without adding prevention. Idea 1 stops the infection; Idea 5 only treats symptoms.

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1: CI from __future__ enforcement | SURVIVES → WINNER | Implement |
| 2: Fix 8 JSX em-dashes | WEAKENED | Bonus Action |
| 5: Python line deletion nightly scope | KILLED | Rejected |
| 3: Human from __future__ removal | Not debated | Bonus Action (if human present) |
| 4: E2E fixture tenant gap | Not debated | Parking Lot — may self-resolve tonight |

Winner chosen: **Idea 1 — Add `from __future__` CI check to pr-check.yml**

Confidence: **HIGH**
- Root cause confirmed (Check 2 bypassed by all non-local commit paths)
- Mechanism proven (nightly creates CI YAML files — AUTONOMOUS-EXECUTABLE)
- Impact: systemic prevention regardless of commit path
- Risk: low (additive YAML step, specific pattern, zero false positives in current codebase)
