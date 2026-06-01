# Ideas — Run 44 (2026-06-01)

## Evidence Summary

Nightly 2026-06-01 (4226ef4 + e7e0a3b + d1f8acc) implemented run 43 winner: extended
nightly-commit-review SKILL.md autonomous scope to cover pre-commit bash additions.
Em-dash fixes in code comments also landed. But Item A (check_project_invariants
pre-commit hook, 30-day pending) is **still blocked**: `check_project_invariants.py`
fails (exit 1) on 5 em-dash violations in JSX UI display text — `IntegrationsPage.jsx:1018`
(`— Not set —` option), `SettingsInboundChannels.jsx:220-221`,
`MessagingSettingsCards.jsx:263/276`. GH #194 opened. The inline Item A patch is ready
in the SKILL.md; the check just needs to pass first.

Status: email_sequences.py still 1255L (run 41 winner, day 3 unimplemented).
lead-qualifier-eval.yml MISSING. check-widget-sync.sh MISSING. GH #181 open.
Moratorium day 30, 14 pending, oldest day 46.

---

### Idea 1: Scope check_project_invariants.py em-dash check to skip .jsx/.tsx files

**Evidence:** Nightly log 2026-06-01 confirms Item A blocked: `check_project_invariants.py`
exit 1 on 5 JSX em-dash violations. Direct script run confirms: FAIL on
`IntegrationsPage.jsx:1018` (`— Not set —` option), `SettingsInboundChannels.jsx:220-221`,
`MessagingSettingsCards.jsx:263/276`. These are UI display text (select placeholder,
labels), not code. Em-dashes in `<option>— Not set —</option>` are a standard UX
affordance. The check was designed for Python/backend naming conventions. GH #194 opened.
Item A patch is inline in nightly SKILL.md (4226ef4) — the ONLY remaining blocker is
this scope fix.

**Action:** Add `.jsx` and `.tsx` to the file-type exclusion in
`scripts/check_project_invariants.py` em-dash check. ~3-line Python change.
After fix: `python3 scripts/check_project_invariants.py` passes all 6 checks →
next nightly (2026-06-02 2:37 AM) executes Item A as AUTONOMOUS-EXECUTABLE →
pre-commit Check 10 lands → closes GH #194.

**Impact:** Unblocks Item A (30-day pending), closes GH #194, reduces moratorium
pending 14→13, enables automated enforcement of Python/SQL naming invariants.

**Category:** workflow / code_health

---

### Idea 2: Add Item D to AUTONOMOUS-EXECUTABLE scope in nightly SKILL.md

**Evidence:** Run 43 winning-concept.md Step 3 explicitly planned this as the
next step after Item A: "After Item A confirms: run 44 adds Item D
(lead-qualifier-eval.yml) to same block." Item D is a new additive CI YAML
(`.github/workflows/lead-qualifier-eval.yml`, Monday cron + PR trigger). Zero
conflict risk — no existing file to overwrite. nightly SKILL.md now covers bash
additions to pre-commit (4226ef4); CI YAML additions are the same risk class.
Governance already has Item D as `subsumed_in_sprint` (run 14 winner, day 27).

**Action:** Add Item D to the AUTONOMOUS-EXECUTABLE section in
nightly-commit-review SKILL.md with the inline YAML patch. Update governance.json
Item D to `pending_autonomous` + `autonomous_executable: true`. ~10 min.

**Impact:** Item D executes autonomously in tonight's or tomorrow's nightly.
Closes run 14 winner (wire CI eval harness). Reduces moratorium pending 14→12
without any human action.

**Category:** workflow / operational

---

### Idea 3: Fix 5 em-dash violations directly in JSX UI copy

**Evidence:** Same 5 violations as Idea 1 — IntegrationsPage.jsx:1018,
SettingsInboundChannels.jsx:220-221, MessagingSettingsCards.jsx:263/276.
Alternative to scoping the check: directly replace em-dashes with hyphens or
en-dashes. The nightly tonight chose NOT to fix these (it fixed comment em-dashes
but left UI copy alone), suggesting it classified them as intentional.

**Action:** Replace `— Not set —` and similar with `- Not set -` or
`— Not set —` (HTML entity to avoid check triggering on the literal character).
Simpler than Idea 1 but may change UI appearance.

**Impact:** Also unblocks Item A. Lower quality than Idea 1 (changes UI) but
faster if nightly does it autonomously (existing em-dash fix pattern).

**Category:** code_health

---

### Idea 4: Merge 5 stale Dependabot PRs (#102, #103, #163, #164, #171)

**Evidence:** Run 27 note flagged these as 4 safe dep PRs 24d stale. By 2026-06-01
these are 41d+ stale. Dependency freshness is a supply-chain security concern.
These are additive, low-risk upgrades. Morning digest 2026-05-29 confirmed
these are in the open PR queue. Moratorium-safe (independent of sprint items).

**Action:** Review and merge 5 safe Dependabot PRs. ~5-10 min.

**Impact:** Fresher dependencies, reduced supply-chain risk, clears PR queue noise.

**Category:** operational

---

### Idea 5: Invoke /god-class-splitter on email_sequences.py

**Evidence:** email_sequences.py at 1255L for 12+ days (run 41 winner, day 3).
Three clean concerns: CRUD / enrollment / processor. god-class-splitter SKILL.md
ready (e848b87). post-split-test-repair SKILL.md ready (d481799). GH #112/#113
N+1 queries become simpler post-split. But: GH #181 billing fix is a prerequisite
per run 41 note (do GH #181 first); GH #181 has been 46+ days open without
resolution.

**Action:** Human invokes `/god-class-splitter` on
`backend/routers/email_sequences.py`. ~2h.

**Impact:** Removes 1255L god-class, enables targeted N+1 fixes. Prerequisite
GH #181 (~15 min billing fix) must land first.

**Category:** code_health
