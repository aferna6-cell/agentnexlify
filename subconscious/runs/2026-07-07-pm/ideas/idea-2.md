# Idea 2: Add brain/INGESTION-LOG.md to Subconscious Phase 2 Evidence

**Evidence:** Runs 79, 80, 81 all tracked brain connector status via governance.json (stale, updated only when a run explicitly writes it) or brain/state.json. Phase 2 of SKILL.md (line 49-73) lists `docs/dev-knowledge/bug-patterns.md`, `docs/dev-knowledge/customer-gaps.md`, `knowledge-base/INDEX.md`, skill-discovery reports, and daily logs — but NOT `brain/INGESTION-LOG.md`. This run had to manually check INGESTION-LOG.md to confirm 7 consecutive daily failures (GitHub 403, SUPABASE_ACCESS_TOKEN missing). run_82_mandate explicitly names this as secondary target: "Secondary: INGESTION-LOG.md in subconscious Phase 2 (after GH #394 resolved)."

**Action:** Add one line to `.claude/skills/subconscious/SKILL.md` Phase 2 evidence block: `cat brain/INGESTION-LOG.md | tail -20  # connector health`. Also add it to the "Also read:" list alongside bug-patterns.md and customer-gaps.md.

**Impact:** Every future run gets live connector health from the authoritative source. Eliminates reliance on governance.json or brain/state.json for connector status (both can be 24h+ stale). Takes 2 minutes to implement. Compounds across all future runs (run 83+).

**Category:** workflow_efficiency

**Confidence pre-debate:** HIGH — evidence-backed, atomic, zero risk, one-line change.
