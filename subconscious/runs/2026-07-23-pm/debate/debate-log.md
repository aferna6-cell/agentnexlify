# Debate Log — Run 101 (2026-07-23-pm)

Top 3 ideas debated: Idea 1 (Step 9G), Idea 3 (SHOW_BOOKING_PANEL), Idea 2 (credential tracking).

---

## Round 1: Idea 1 — Step 9G Carry-Forward

**Challenge:**
KB ran today (2026-07-23 log entry). If the knowledge base is now fresh, is Step 9G still urgent? The manual CCR session patched the staleness. Maybe wait one more cycle to see if a natural opportunity arises.

**Defend:**
Manual CCR session is not a fix — it's a workaround. The automated kb-autopopulate.yml workflow remains broken. ANTHROPIC_API_KEY and VOYAGE_API_KEY are still absent from GH Actions secrets. Next automated run (tonight's nightly at 2:37 AM) will see KB as fresh (manual run was today), so Step 9F won't fire, and Step 9G won't get a live test — but two nights from now, staleness resumes and the same broken workflow runs again. The mandate from run 100 is explicit: check Step 9G presence. It is absent. Carry-forward fires. The channel (SKILL.md bash block) is proven across 5 prior steps. This is XS effort (~30 lines) with HIGH impact.

**Verdict: SURVIVES.** Carry-forward mandate + proven channel + immediate load-bearing. Winner candidate.

---

## Round 2: Idea 3 — SHOW_BOOKING_PANEL Funnel Completeness

**Challenge:**
19 new lines in bug-patterns.md is circumstantial. The file adding patterns doesn't prove a bug exists — it may be proactive documentation. The commit e9b4972 landed today; it hasn't had time to show failure signals. We'd be investigating a potential gap before evidence of breakage.

**Defend:**
True, 19 new bug-pattern lines is a yellow flag, not confirmed breakage. But the SHOW_BOOKING_PANEL feature is revenue-critical (booking = primary conversion) and the new file (widget_chat_booking_action.py, 33L) could easily be unwired from main.py. Past god-class splits in this project consistently required main.py registration fixes. The nightly review's guardrail tripped on LOC (0 autonomous fixes) — so these wiring gaps weren't checked by the nightly tool either.

**Verdict: SURVIVES as investigation idea, NOT as winner.** High potential impact but speculative — needs investigation, not a SKILL.md edit. Park in improvement-backlog for run 102 with "verify wiring" action.

---

## Round 3: Idea 2 — Credential Tracking Gap

**Challenge:**
Updating `ops/credential-rotation-schedule.md` to add VOYAGE_API_KEY and SUPABASE_ACCESS_TOKEN is housekeeping, not improvement. Step 9E already reports "SUPABASE_ACCESS_TOKEN: unknown_state." Adding two doc lines doesn't fix the credentials — it just makes the already-visible gap more structured.

**Defend:**
Fair. The tracking update has low standalone impact. The real fix is setting the secrets in GH Actions, which requires human action (not autonomous). Step 9G (Idea 1) actually addresses the root problem more forcefully by triggering the workflow and surfacing the exact failure. Adding doc tracking is additive but lower leverage than Step 9G.

**Verdict: WEAKENED.** Parking lot. Step 9G is the higher-leverage intervention on the same failure surface.

---

## Final Ranking

| Rank | Idea | Verdict |
|------|------|---------|
| 1 | Step 9G carry-forward | **WINNER** |
| 2 | SHOW_BOOKING_PANEL funnel | Parking lot (run 102 investigation) |
| 3 | Credential tracking | Parking lot (lower leverage) |
| 4 | email_sequences split verification | Parking lot (likely already correct) |
| 5 | Voice workforce bridge | Insufficient evidence, skip |
