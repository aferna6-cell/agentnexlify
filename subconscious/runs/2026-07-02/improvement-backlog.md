# Improvement Backlog — Run 77 (2026-07-02)

## Active

- **[SKILL.md patch]** Add file-location verification to subconscious Phase 2 evidence gathering — grep for function symbol before concluding "unimplemented" from absent file path. AUTONOMOUS-EXECUTABLE, nightly scope. `.claude/skills/subconscious/SKILL.md`.

## Parking Lot (survived debate, not chosen this run)

- **Plan-name guard pre-commit (Check 14)** — XS, AUTONOMOUS-EXECUTABLE. Scan Python files for retired plan names (`foundation`/`operations`). No recent incident; pick up opportunistically when touching `scripts/hooks/pre-commit`. Confidence: MEDIUM.
- **Custom automation templates (cross-industry)** — Medium effort. KILLED this run (moratorium). Re-evaluate run 78+ if moratorium lifts. Cross-industry value, leverages Agent OS infrastructure.
- **Trial-to-member conversion tracking** — Low effort. Fitness-vertical specific. Re-evaluate when fitness tenant count warrants.

## Rejected This Run

- **Custom automation templates** — KILLED. Moratorium active, Medium effort, adds to human queue. Not wrong as an idea; wrong timing.

## Bonus Action (XS, run alongside winner)

- Update `docs/dev-knowledge/customer-gaps.md`: move "Lead source analytics" from Open → Resolved (confirmed implemented run 2, AnalyticsPage.jsx BarChart per run 9 governance correction).

## Questions for Next Run (Run 78)

1. **Has the SKILL.md patch been applied?** If not, file explicit nightly directive.
2. **Has SMS Dashboard shipped?** If yes: true pending = 1 < 2 → moratorium exits → recommend first Medium-effort feature (Custom automation templates or AI-to-Human Handoff v2 if new approach exists).
3. **What is the actual path of email_sequences.py (or its split modules)?** Grep the codebase to either find it or confirm the split happened, then update run 41's active_direction accordingly.
4. **Is Widget Sync Guard (run 7, check-widget-sync.sh) still not created?** If so: the true pending is still SMS Dashboard + Widget Sync Guard = 2 = moratorium stays active.
