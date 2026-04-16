# Debate 2: Silent Frontend Error Audit + React ErrorBoundary

## Steel-Man

62 silent catch blocks are 62 open wounds in the frontend. Each one is a place where errors disappear without trace — no user notification, no log, no metric. The backend equivalent (bare `except:`) has been blocked by pre-commit hook for months. The frontend has no equivalent protection. The 4 fully-silent catches have persisted as a P2 task for 3+ days with zero action, indicating the team is under-prioritizing a real maintenance debt. React ErrorBoundaries are trivial to add and prevent the most jarring failure mode: an uncaught exception that renders a blank white page.

## Hard Objections

**Objection 1: 62 catch blocks is a cosmetic change, not a functional fix. None of these have caused a reported bug.**

Fixing error handling doesn't fix underlying bugs — it just makes them visible. If nothing is broken, you're adding noise (console.error spam) for no user-visible benefit.

*Rebuttal:* The silence *is* the bug. The lead_captured RLS bug was invisible for days because errors were swallowed. Frontend catches swallowing errors means the same class of silent failure is possible in the UI. We don't know what's broken because we can't see it. Making errors visible is a prerequisite for fixing them — it's not cosmetic, it's a diagnostic prerequisite.

**Objection 2: 62 files × review + edit is tedious developer work that produces zero features. Poor use of a dev sprint.**

This is maintenance work competing with feature work (AI handoff, industry gaps) that directly drives retention and revenue. The ROI case is weak compared to idea-1.

*Rebuttal:* This is legitimate — the direct revenue impact is lower than AI handoff. However, the cost is very low (1–2 days) and the risk of silent errors causing data loss or failed onboarding is non-zero. If the wrong catch is silencing an onboarding wizard error, we've lost a signup without knowing it. That said, this objection is the reason this idea should be ranked below AI handoff.

**Objection 3: React ErrorBoundary will catch unhandled exceptions in renders, but the 62 catches are explicit `.catch()` on async operations. ErrorBoundary doesn't cover those.**

Two separate problems are being conflated: async error swallowing (the 62 catches) and synchronous render crashes (ErrorBoundary domain). Mixing them dilutes focus.

*Rebuttal:* Valid technical point. They should be treated as two separate subtasks: (a) upgrade the 4 fully-silent catches — trivial 30-min task, (b) add ErrorBoundary wrappers — separate 2-hour task. Together they form a complete frontend error visibility upgrade. Separating them clarifies scope and lets the easy part be done immediately.

## Verdict

**Modified scope — split into two discrete tasks.** 
- Task A: Fix 4 fully-silent catches (30 min). Should be done regardless of what else ships.
- Task B: ErrorBoundary wrappers on 3 highest-risk pages (2 hours). Separate PR.
- The "62 catches" audit should become a follow-up, not part of this improvement cycle.

**Final verdict: SECONDARY candidate. Excellent maintenance work but outranked by AI handoff on impact-to-effort ratio. Could be a parallel same-day task alongside the winner.**
