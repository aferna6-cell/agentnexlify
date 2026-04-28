---
name: ddup
description: "Use when asked to /ddup or dedupe duplicate Agent Nexlify skills, docs, agents, widget files, routes, or repeated workflow surfaces safely."
version: 1.0.0
origin: claude
user_invocable: true
allowed_tools: [Read, Bash, Grep, Glob]
depends_on: [dead-code-sweep]
triggers: ["/ddup", "ddup", "dedupe", "find duplicates", "duplicate docs", "duplicate skills", "consolidate overlap"]
---

# Ddup

## When to Use
- The user asks to find or reduce duplicated Agent Nexlify surfaces.
- Skills, docs, agents, widget files, prompts, routes, or tests appear to overlap.
- A cleanup should start with evidence and candidates instead of immediate deletion.

## When NOT to Use
- Do not use as a blind dead-code remover.
- Do not use when the user already identified one exact file to edit.
- Do not use for generated artifacts that are intentionally mirrored by build or publish steps.

## Read First
- Define the duplicate surface before searching.
- Inspect existing canonical sources, generated mirrors, sync scripts, and ownership docs for the touched surface.
- Check git status so user work is preserved.

## Workflow
1. Search for near-duplicates with `rg`, `rg --files`, file names, trigger phrases, route names, exported symbols, and repeated headings.
2. Classify each candidate:
   - `merge`: two live sources should become one canonical source.
   - `alias`: both should stay, but one should point to the other.
   - `generated mirror`: keep both and verify the sync rule.
   - `stale`: likely removable after confirmation.
3. Produce a candidate table with file paths, evidence, risk, recommended owner, and proposed action.
4. Ask for confirmation before deleting, moving, or collapsing any candidate.
5. After approval, make the smallest consolidation and run targeted checks for the touched surface.

## Output Format
Return a candidate table with:
- File paths
- Duplicate evidence
- Classification
- Risk
- Recommended owner
- Proposed action

Then list confirmation needed before edits.

## Constraints
- Never delete files during the discovery pass.
- Treat `widget/` and `frontend/public/widget/` mirrors as intentionally duplicated until proven otherwise.
- Treat migrations, archived launch artifacts, and public API surfaces as high-risk.
- Preserve user changes and unrelated dirty work.
- If confidence is below high, recommend an alias or doc pointer instead of removal.

## Examples
- Use when asked: "/ddup the skill system"
- Use when asked: "find duplicate docs about launch readiness"
- Use when asked: "dedupe widget configuration surfaces"
- Do not use when asked: "remove this one unused import"
