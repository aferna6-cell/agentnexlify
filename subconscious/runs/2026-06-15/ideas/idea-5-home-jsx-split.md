### Idea 5: Split Home.jsx god-class (~1171L) into sections

**Evidence:** Home.jsx is 1171L (Rule 9: factor at 600+). Never targeted by subconscious. Large batch of launch-readiness commits (651c6fe) added IntegrationHealthDashboard.jsx (633L), TeamActivityPage.jsx (148L), AgentQualifierSettings.jsx (197L) — all new pages. The dashboard is growing. Home.jsx as central routing/layout hub is the biggest unmaintained mass.

**Action:** Invoke /god-class-splitter on frontend/src/pages/Home.jsx — split into HomeHero.jsx, HomeFeatures.jsx, HomePricing.jsx (or whatever concerns exist). Run /post-split-test-repair for import paths.

**Impact:** Reduces merge conflict risk on most-touched file. Improves frontend maintainability. HUMAN-REQUIRED (frontend god-class splits need visual verification).

**Category:** code_health
