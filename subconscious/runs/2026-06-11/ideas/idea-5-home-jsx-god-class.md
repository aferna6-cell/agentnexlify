### Idea 5: Split Home.jsx (1171L) Before it Reaches God-Class Threshold

**Evidence:** `frontend/src/pages/Home.jsx` at 1171L after 7c8825c ("Home redo + Agent OS uploads/image-gen + Instagram connector"). God-class threshold per user-rules.md Rule 9 is 600L — Home.jsx is already 2x that. A single PR rewrote and expanded it to 1171L. Prior splits in this project (widget_helpers 6cf4646, email_sequences 1255L pending) confirm the pattern: files balloon during feature sprints and become hard to review/debug. `AgentOS.jsx` is also at 790L.

**Action:** Run `/god-class-splitter` on `frontend/src/pages/Home.jsx`. Proposed split: `HomeHero.jsx` (above-fold content), `HomeAgentOSSection.jsx` (agent OS integration cards), `HomeAnalyticsSection.jsx` (metrics/charts).

**Impact:** Reduces blast radius for Home page changes. Improves reviewability. Prevents future merge conflicts on a hot file. HUMAN-REQUIRED (god-class-splitter is a 1-2h compound task, not autonomous).

**Category:** code_health
