# Debate Log — Run 44 (2026-06-01)

Top 3 ideas debated: Idea 1 (scope em-dash check), Idea 2 (add Item D to autonomous scope),
Idea 5 (email_sequences split). Ranked by impact on moratorium exit path.

---

## Idea 1 — Scope check_project_invariants.py em-dash check to skip .jsx/.tsx

### Round 1

**Challenge:** Is scoping the em-dash check to skip JSX the right fix, or
are these JSX em-dashes genuinely wrong and should be fixed?

**Defend:** The 5 violations are all in UI display text: `— Not set —` in
`<option>` elements (select placeholder), button/label text. Em-dashes in
dropdown placeholders are a standard UX convention — they visually indicate
"nothing selected" better than a hyphen. Replacing them degrades UX.
`check_project_invariants.py` was built to catch backend naming violations
(client_id vs tenant_id, em-dash in Python docstrings). The JSX context is
fundamentally different. Scoping is principled, not a workaround.

**Supporting evidence:** The nightly review tonight fixed em-dashes in JS
code comments (`os-inbound.js` JSDoc) but explicitly DID NOT fix the JSX
option values — confirming its own classification: those are intentional.

### Round 2

**Challenge:** This creates a blind spot: em-dashes accidentally introduced
into JSX comments or string templates won't be caught.

**Defend:** JSX files run through ESLint on `npm run build`. Frontend build
is in pre-push (verified passing). Em-dash typos in JSX code would be caught
by TypeScript/ESLint before reaching pre-commit. The invariant check's value
on JSX is marginal; its value on Python/SQL/HTML is high. Scoping to
non-JSX preserves all high-value coverage with zero loss.

Additionally: runs 10-12 identified this exact issue 6 weeks ago ("em-dash
check needs scoping fix to skip .jsx/.tsx" — run 12 memory entry). This has
been known since May 1; the fix has just never been prioritized.

### Round 3

**Challenge:** Is this the highest-leverage item right now? Item A has been
blocked by this same em-dash issue since May 5 (first time invariants.py
hit a JSX violation). Isn't the real fix just to wire Item A with a different
pre-condition (skip if any JSX em-dash present)?

**Defend:** No — the better fix is principled scope enforcement. Wiring Item A
with "skip if JSX violations" would mean Item A fires even when
check_project_invariants.py would fail on non-JSX violations. The scope fix
is cleaner: after it lands, `check_project_invariants.py` correctly passes
on a clean backend and ignores legitimate JSX UI copy.

Also: run 43 SKILL.md extension already provides the automation. The
scope fix IS the last mile. After this 3-line change, the full chain
fires tonight with zero further human action.

**Verdict: SURVIVES — highest leverage, unblocks 30-day pending Item A.**

---

## Idea 2 — Add Item D to AUTONOMOUS-EXECUTABLE scope in nightly SKILL.md

### Round 1

**Challenge:** Run 43 explicitly said to add Item D AFTER Item A confirms.
If we add Item D now and Item A is still blocked, does that create confusion?

**Defend:** Item D (lead-qualifier-eval.yml) has zero dependency on Item A.
It's a new CI YAML file — no pre-condition check needed. The sequencing
recommendation in run 43 was conservative ("confirm Item A first"), but
technically there's no conflict. Adding Item D to autonomous scope now means
it can land tonight regardless of Item A's status.

### Round 2

**Challenge:** The nightly SKILL.md is getting multiple AUTONOMOUS-EXECUTABLE
entries. Does complexity increase misclassification risk?

**Defend:** The pattern is clear and consistent: each entry has (1) file path,
(2) pre-condition, (3) inline patch. Item D has no pre-condition. Nightly
has successfully executed 5/5 correctly-scoped AUTONOMOUS-EXECUTABLE items.
Complexity here is controlled template growth, not open-ended expansion.

### Round 3

**Challenge:** Is this more impactful than Idea 1 right now?

**Defend:** Idea 1 unblocks Item A (30-day pending) AND closes GH #194.
Idea 2 reduces pending 14→12. Idea 1 is more catalytic — it also enables
check_project_invariants.py enforcement which was the original goal of
run 8 (day 37). Idea 1 > Idea 2 on net impact.

**Verdict: WEAKENED — valid, parking lot. Should be proposed in run 45
after Idea 1 lands and Item A confirms.**

---

## Idea 5 — Invoke /god-class-splitter on email_sequences.py

### Round 1

**Challenge:** GH #181 billing fix is a stated prerequisite per run 41
winning-concept.md. GH #181 has been open 46+ days without resolution.
Recommending a prerequisite-blocked item as winner is a repeat of the
GH #181 rejection loop (5 consecutive wins without implementation,
rejected_paths since run 35). Same failure mode?

**Defend:** GH #181 is listed as a prerequisite because billing.py
constants are referenced in email sequence enrollment (plan tier gating).
However, the split itself is separable — email_crud.py, email_enrollment.py,
email_processor.py don't change the billing logic, just move it to cleaner
modules. The prerequisite was a sequencing caution, not a hard blocker.

**Counter-challenge:** The sequencing note says "GH #181 billing fix (~15 min,
human required) before starting split." If the split modifies
`email_enrollment.py` which calls billing functions, and billing.py has
wrong constants at that point, we'd be splitting code that already has a
silent bug. The post-split test suite would certify the wrong behavior.

### Round 2

**Challenge:** This is the 4th recommendation as a winner or active_direction
(runs 35, 38, 41, and now implicitly). What's different this time?

**Defend:** New: post-split-test-repair SKILL.md now exists (d481799, 2026-05-30).
The last prerequisite tooling is in place. But GH #181 is still blocking
per the sequencing note, and the email_sequences split is M-effort (~2h human).
Idea 1 is S-effort (~5 min) with higher autonomous implementation probability.

### Round 3

**Challenge:** Moratorium is at day 30. MEDIUM-effort human work is exactly
what the moratorium is supposed to prevent — it blocks new recommendations
until pending items are cleared. Adding another M-effort recommendation
deepens the backlog.

**Defend:** This is a standing active_direction (run 41 winner). Re-recommending
it as run 44 winner would be repeating it without new evidence. The only new
evidence is post-split-test-repair SKILL.md existence — not sufficient to
override the moratorium priority ordering.

**Verdict: KILLED as winner — stands as active_direction, propose after GH #181
resolves and moratorium exits. Not enough new evidence to justify run 44 winner slot.**

---

## Synthesis

| Idea | Verdict | Notes |
|------|---------|-------|
| 1 — Scope em-dash check to skip JSX | SURVIVES → WINNER | Unblocks Item A (30d), closes GH #194, 3-line fix |
| 2 — Add Item D to AUTONOMOUS scope | WEAKENED → parking lot | Valid, propose run 45 |
| 3 — Fix JSX violations directly | KILLED | Changes UI, worse than Idea 1 |
| 4 — Merge Dependabot PRs | WEAKENED → bonus action | Independent, ~5 min, valid |
| 5 — email_sequences split | KILLED as winner | Active_direction stands, GH #181 blocks |
