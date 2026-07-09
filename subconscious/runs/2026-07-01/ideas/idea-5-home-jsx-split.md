# Idea 5: Home.jsx God-Class Split (1006L)

**Evidence:** `frontend/src/pages/Home.jsx` confirmed 1006 lines (parked run 74). CLAUDE.md Rule 9: don't extend god classes >600L. Run 74 backlog notes it explicitly. `god-class-splitter` skill available (e848b87). Post-split-test-repair skill available (d481799). Natural split: HeroSection + LeadCapture + Testimonials/Social + CTASection.

**Action:** Invoke `/god-class-splitter` on `frontend/src/pages/Home.jsx`. Split into 3-4 component files. Run post-split-test-repair to repoint stale imports. M-effort, human required.

**Impact:** Reduces blast radius on marketing page edits. Enables parallel frontend dev. Resolves god-class debt that's been accumulating since homepage launch.

**Category:** code_health

**Concern:** M-effort. Human required. Moratorium active. No blocking production bugs. Should wait until SMS Dashboard and Zapier fix ship. Parked by run 74 — no new evidence to unpark early.
