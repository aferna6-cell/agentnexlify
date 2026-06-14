# Ideas — Run 50 (2026-06-05)

## Evidence Digest

- **Run 49 winner IMPLEMENTED** by nightly review (8db33df, 2026-06-05): 5 em-dash substitutions in JSX UI strings applied autonomously.
- **check_project_invariants.py exits 0** — all 6 checks PASS (confirmed live this session). Item A pre-condition met.
- **Item A auto-wires TONIGHT**: nightly SKILL.md §Item A reads "Execute when script passes clean" — condition now met. Check 10 will be added to pre-commit at 2:37 AM.
- **Item B (scripts/check-widget-sync.sh) MISSING** — 43 days. 3 widget JS copies confirmed at widget/, frontend/public/widget/, landing-page-v2/widget/. No sync guard exists.
- **GH #181 still open** — billing.py:263 AMOUNT_TO_PLAN confirmed missing `15000: "autopilot"` and `25000: "professional"` (live check). Check 11 WARNING fires on every commit.
- **email_sequences.py 1255L**, 17 functions — run 35/41 active_direction, fully unblocked, M-effort.
- **Zero production code commits** in 4 days.
- **Moratorium day 35**, ~14 pending after run 49 correction.

---

### Idea 1: Extend Nightly Scope + Mark Item B AUTONOMOUS-EXECUTABLE
**Evidence:** Nightly SKILL.md autonomous scope covers pre-commit additions and SKILL.md creation but NOT scripts/ new file creation or pre-push additions. Three prior scope extensions (runs 40/43/47) each resulted in successful autonomous execution in the next nightly cycle. Widget copies confirmed at 3 paths (all byte-identical currently). Item A closes tonight — Item B is the natural next domino. SKILL.md §Item A shows the inline-script pattern works.

**Action:** (a) Add two bullets to nightly-commit-review SKILL.md LOW-risk autonomous scope: "New bash scripts in `scripts/` directory" + "Additions to `scripts/hooks/pre-push`". (b) Add Item B block to SKILL.md with full `check-widget-sync.sh` content and pre-push patch. (c) Update governance.json Item B (run 7/15) status to `pending_autonomous` + `autonomous_executable: true`.

**Impact:** Widget sync guard created autonomously without human action. Closes 43-day run 7/15 gap. Pre-push hook gains integrity check before every push. Moratorium pending drops when Item B closes.

**Category:** code_health / workflow

---

### Idea 2: GH #181 — Billing.py Fix (Interactive Human Action)
**Evidence:** Path confirmed live: `backend/routers/billing.py:263`. AMOUNT_TO_PLAN missing `15000: "autopilot"` (autopilot $150/mo) and `25000: "professional"` (professional $250/mo). Check 11 WARNING fires on every commit. Two prior failed attempts targeted wrong path (now resolved). ~15 min human, S-effort.

**Action:** Add `{15000: "autopilot", 25000: "professional"}` to AMOUNT_TO_PLAN dict; remove backwards test assertions in `test_billing_amount_to_plan.py:38-44`; add current-price assertions; update `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`.

**Impact:** Closes 50-day billing gap, silences Check 11 WARNING, fixes CI-certifying-broken-state problem. Closes GH #181.

**Category:** code_health

**NOTE:** In `rejected_paths` as a winner (5-consecutive-run threshold). Cannot be chosen as winner per governance.

---

### Idea 3: Zapier API Key plan_status Security Fix (Parallel-Track GH Issue)
**Evidence:** GH #107 filed 2026-04-30 (36+ days). `backend/services/zapier_auth.py::_get_api_key_client` resolves keys without `plan_status` check. Cancelled tenants with un-revoked keys bypass tier gate. Parking lot ROI 2.5 ("Route via issue-to-pr-loop, NOT subconscious winner queue"). Security parallel-track exception used in run 29 (AI-to-Human Handoff GH issue).

**Action:** Create GH issue tagged `ai-ready` for issue-to-pr-loop: fix `_get_api_key_client` to add `plan_status IN ('active','trialing')` filter + regression test. ~10 lines.

**Impact:** Closes security gap. ~10-line fix prevents cancelled tenant data exfiltration via un-revoked Zapier keys.

**Category:** security

---

### Idea 4: email_sequences.py God-Class Split
**Evidence:** 1255L confirmed (17 functions). 3 clean concerns: CRUD/enrollment/processor. god-class-splitter SKILL.md ready (e848b87). post-split-test-repair SKILL.md ready (d481799). GH #112/#113 N+1 bugs (~2.3 ROI) become simpler post-split. Run 35/41 active_direction.

**Action:** Invoke /god-class-splitter on email_sequences.py — split into email_crud.py, email_enrollment.py, email_processor.py. GH #181 is prerequisite (do first).

**Impact:** Splits 1255L into 3 modules <600L each. Simplifies N+1 fix. Reduces blast radius on email feature bugs.

**Category:** code_health

**NOTE:** M-effort (~2h), moratorium still active (day 35).

---

### Idea 5: AI-to-Human Handoff v1 — Tag as ai-ready GH Issue
**Evidence:** Run 4, 50 days oldest pending, CRITICAL gap all 7 industries. Agent OS (os_outbound_mirror.py, PR #188 merged) reduces scope from ~3 days to ~1 day. Parking lot note: "do not re-propose as winner until moratorium exits."

**Action:** Tag existing run 4 GH issue as `ai-ready` for issue-to-pr-loop pickup.

**Impact:** Closes Critical 50-day customer value gap. Enables explicit handoff trigger in widget conversations.

**Category:** customer_value

**NOTE:** Parking lot constraint. No new evidence since run 38. Moratorium still active.
