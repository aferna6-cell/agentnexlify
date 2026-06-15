# Debate Log — 2026-06-15

Top 3 ideas ranked by impact. Each runs 3 challenge → defend rounds.

---

## Idea 1: Add pre-commit Check 13 — `from __future__ import annotations` guard

### Round 1

**Challenge:** check_project_invariants.py passes clean RIGHT NOW. The violations are gone. Why add a guard for a problem that's already solved?

**Defend:** Violations were gone after run 55 too — then PR #238 (auth.py split, one day later) introduced 3 new ones. 100% recurrence on every router split. check_project_invariants checks the committed state of files, not staged state. Pre-commit Check 13 fires at commit time and blocks the violation before it lands. The problem is in the workflow (split creates new file → developer forgets → violation ships), not in the current codebase state.

---

### Round 2

**Challenge:** Run 56 already recommended this. It's been 3 days and nightly hasn't executed it. What's different now?

**Defend:** The AUTONOMOUS-EXECUTABLE mechanism for bash additions to pre-commit was confirmed working: Check 11 (061582c) and Check 12 (ca3ce68) were both added autonomously by nightly. The nightly SKILL.md scope extension (run 43, 4226ef4) explicitly covers pre-commit bash additions. The reason run 56 hasn't fired is execution timing (nightly runs 2:37 AM) — this run's governance update marking it pending_autonomous again gives the nightly review the explicit instruction it needs tonight.

---

### Round 3

**Challenge:** Is this the highest-leverage thing to do right now? The project just shipped integration encryption, WordPress plugin, and qualifier moat — all new code surface. Shouldn't the recommendation target those riskier areas?

**Defend:** The new features (encryption, qualifier, WordPress) were reviewed clean by nightly 87b5eb8 — no bugs found. Check 13 is autonomous and zero human time cost. The highest-leverage things that require human attention (AI-to-human handoff, email split) are in the parking lot. The autonomous/human resource pools are separate: Check 13 consumes ONLY nightly time (~5 min), not human dev time. Blocking the recurrence of a 422-all-endpoints bug class at near-zero cost is always the right call.

**Verdict: SURVIVES → WINNER**

---

## Idea 2: Create migration 149_audit_log.sql

### Round 1

**Challenge:** Nightly explicitly called this "acceptable until audit_log lands." Integration secrets are encrypted with authenticated encryption (Fernet) — the encryption is correct. Audit trail is observability, not correctness. Is this actually urgent?

**Defend:** The audit_log gap matters more than "acceptable" implies. integration_key_vault.py is called on every Supabase integration setup/update. With zero audit trail, if a tenant's Instagram token is ever compromised, there is no forensic record of when it was decrypted, from what IP, or by what action. For a product heading to paying B2B customers, that's a compliance gap that will surface in due diligence.

---

### Round 2

**Challenge:** Schema changes require human approval. This is NOT autonomous-executable. And creating audit_log before the product team designs the schema risks locking in the wrong columns (too many auth-logging teams have regretted narrow schemas).

**Defend:** Fair — the schema concern is real. A minimal `(tenant_id, event_type, entity_id, metadata jsonb, created_at)` covers the current `_write_audit` call sites and leaves metadata jsonb flexible for future fields. But the human-approval barrier and schema design risk justify parking this.

---

### Round 3

**Challenge:** No GH issue exists for audit_log. No customer has complained. The gap is "awareness only" per the team's own review. Pick something with a harder forcing function.

**Defend:** Conceded. No customer impact, no GH issue, no human pressure. The encryption feature itself is correct — audit trail is enhancement. This is the right item for the parking lot but the wrong winner when a higher-urgency autonomous item (Check 13) exists.

**Verdict: WEAKENED → Parking lot (audit_log table, ROI 1.8, no urgency forcing function)**

---

## Idea 3: AI-to-Human Handoff v1

### Round 1

**Challenge:** This has been recommended as a subconscious winner 4 times (runs 4, 21, 38 primary + run 29 GH-issue variant). 60 days without implementation. What's genuinely different this run that makes it implementable?

**Defend:** os_outbound_mirror.py merged (PR #188, 2026-05-27) — this is genuinely new infrastructure. Run 38 estimated implementation at ~1 day (down from ~3 days). Momentum: the project just shipped 5 major features in 3 days (launch-readiness batch). Run energy is high.

---

### Round 2

**Challenge:** "Momentum is high" is not evidence — it's speculation about developer state. The bottleneck for AI-to-human handoff has never been infrastructure (the infrastructure existed before too). The bottleneck is human decision-making: what triggers count, what's the fallback if owner isn't reachable, how is it scoped to prevent false positives. Those questions are unanswered.

**Defend:** The trigger question has a simple first answer: start with explicit phrases only ("speak to a human", "talk to someone", "call me back") — no ML, no inference. False positives go to zero. This matches the "explicit-trigger-only v1" scope from run 4. Infrastructure + scoping both solved.

---

### Round 3

**Challenge:** Customer value is real, but this is MEDIUM effort (~1 day), human-required, and moratorium is technically still active with 15+ pending items. Picking a 1-day human-required feature over a 10-line autonomous code_health fix is wrong resource allocation.

**Defend:** Can't fully counter this. The autonomous/human resource pools ARE separate, but the winning concept must be singular. Recommending a human-required feature when an autonomous item exists that closes a recurring 422-all-endpoints risk class is wrong priority ordering. AI-to-human handoff is important — it belongs in the parking lot with explicit next-run trigger if Check 13 gets implemented tonight.

**Verdict: WEAKENED → Parking lot (MEDIUM effort, human-required, recurring recommendation with same bottleneck)**

---

## Summary

| Idea | Verdict | Fate |
|------|---------|------|
| Idea 1: Check 13 from __future__ guard | SURVIVES | WINNER |
| Idea 2: audit_log migration | WEAKENED | Parking lot (ROI 1.8) |
| Idea 3: AI-to-Human Handoff v1 | WEAKENED | Parking lot (recurring, human-required) |
| Idea 4: email_sequences.py split | Not debated | Parking lot (run 41 pending_approval stands) |
| Idea 5: Home.jsx split | Not debated | Parking lot (HUMAN-REQUIRED, lower urgency) |
