---
name: subconscious
description: "Self-improvement loop that gathers evidence, generates improvement ideas, debates them, synthesizes one recommendation, and writes artifacts."
version: 1.0.0
origin: claude
user_invocable: true
triggers: ["subconscious", "self-improvement", "improvement loop", "generate improvement ideas", "debate ideas"]
effort: medium
---

# Subconscious Agent — Self-Improvement Loop

A continuous improvement system that compounds. Each run gathers evidence, generates ideas, debates them, picks one winner, and persists the learning so the next run starts smarter.

## Usage

- `/subconscious` — run the full loop
- `/subconscious --dry-run` — ideate and debate only, don't write artifacts

## When to Use
- Running periodic self-improvement cycles to identify workflow or code quality improvements
- Generating and debating improvement ideas with evidence-based reasoning

## When NOT to Use
- Implementing a specific known fix (just do it directly)
- Emergency bug fixes (fix first, improve process later)
- When governance.json has auto_approve set to true and you want human oversight

## The Loop

```
Load Brief → Load State → Gather Evidence → Ideate → Debate → Synthesize → Write Artifacts → Persist Learning
```

### Phase 1: Load Context

1. Read `subconscious/briefs/agentnexlify-improvement.md` — the mission brief
2. Read `subconscious/state/governance.json` — config, frozen ideas, active directions, rejected paths
3. Read last 5 entries from `subconscious/state/memory.jsonl` — recent run history
4. If a previous run exists in `subconscious/runs/`, read the latest `winning-concept.md` and `improvement-backlog.md`

### Phase 2: Gather Evidence

Collect fresh data from these sources:

```bash
# Recent commits
git log --since="3 days ago" --oneline --stat

# Recent bug fixes
git log --since="7 days ago" --oneline --grep="fix"

# Test health
python3 -m pytest tests/ -x --tb=short -q 2>&1 | tail -10

# Skill discovery reports
ls docs/skill-discovery/ | tail -3

# Recent daily logs
ls docs/daily-logs/ | tail -3
```

Also read:
- `docs/dev-knowledge/bug-patterns.md` — recurring bug classes
- `docs/dev-knowledge/customer-gaps.md` — open product gaps
- `knowledge-base/INDEX.md` — what the KB knows

Summarize evidence in 200 words max. Focus on: what changed, what broke, what's missing, what's working.

### Phase 3: Ideate (use Sonnet — cheap, fast)

Generate exactly 5 candidate improvement ideas. Each idea must:
- Reference specific evidence ("commit abc123 showed...", "bug-patterns.md lists...")
- Be atomic — one clear action, not a vague direction
- Include expected impact (time saved, bugs prevented, revenue unlocked)
- NOT be in the `frozen_ideas` list from governance.json
- NOT repeat a `rejected_paths` entry unless new evidence justifies revisiting

Format:
```
### Idea 1: [Title]
**Evidence:** [what data supports this]
**Action:** [specific thing to do]
**Impact:** [expected outcome]
**Category:** [code_health | workflow | agent_performance | customer_value | operational]
```

### Phase 4: Debate (use Opus — judgment, rigor)

For each of the top 3 ideas (ranked by impact), run a challenge-and-defend cycle:

**Challenge:** Attack the idea. Ask:
- Is the evidence strong enough?
- Is this the highest-leverage thing to do right now?
- What could go wrong?
- Has something similar been tried and rejected?
- Is this too similar to the current active direction?

**Defend:** Counter each objection with evidence or reasoning.

**Verdict:** SURVIVES, WEAKENED, or KILLED.

Write the full debate to `subconscious/runs/{date}/debate/debate-log.md`.

### Phase 5: Synthesize (use Opus)

From surviving ideas, pick exactly ONE winner. Write:

**`subconscious/runs/{date}/winning-concept.md`:**
```markdown
# Winning Concept — {date}

## Recommendation
[One clear sentence: what to do]

## Why This, Why Now
[3-4 sentences connecting evidence → action → impact]

## Implementation Sketch
[Bullet list of steps — enough for an agent or human to execute]

## What This Replaces
[What the previous active direction was, if any]

## Confidence
[HIGH / MEDIUM / LOW — based on evidence strength and debate outcome]
```

**`subconscious/runs/{date}/improvement-backlog.md`:**
```markdown
# Improvement Backlog — {date}

## Active
- [The winning concept — 1 line]

## Parking Lot (survived debate but not chosen)
- [Other surviving ideas — may be picked in future runs]

## Rejected This Run
- [Ideas killed in debate, with reason]

## Questions for Next Run
- [What the system should investigate next time]
```

### Phase 6: Persist Learning

1. **Update governance.json:**
   - Set `last_run` to current timestamp
   - Increment `total_runs`
   - Update `active_directions` with winning concept
   - Add killed ideas to `rejected_paths` (with reason and date)
   - If an idea has been rejected 3+ times, add to `frozen_ideas`

2. **Append to memory.jsonl:**
   ```json
   {"date": "2026-04-04", "evidence_summary": "...", "ideas_count": 5, "winner": "...", "confidence": "HIGH", "rejected": ["...", "..."]}
   ```

3. **Write run summary:**
   `subconscious/runs/{date}/run-summary.json`

### Phase 7: Report

Output to terminal:
```
## Subconscious Run — {date}

### Evidence Digest
[2-3 key observations]

### Winner
[One sentence]

### Confidence: HIGH/MEDIUM/LOW

### Debate Summary
- Idea A: SURVIVED → chosen
- Idea B: WEAKENED → parking lot
- Idea C: KILLED — [reason]

### Next Run Should Investigate
[1-2 questions]

Run artifacts: subconscious/runs/{date}/
```

### Phase 8: Commit

```bash
git add subconscious/
git commit -m "subconscious: run {date} — {winning concept title}"
```

## Approval Gate

The subconscious RECOMMENDS but does NOT implement. Implementation requires:
1. Human reviews `winning-concept.md`
2. Human says "do it" or "reject"
3. If rejected: the system logs the rejection reason in governance.json for future runs

To implement an approved recommendation:
```
/subconscious --implement
```
This reads the latest winning-concept.md and executes the implementation sketch.

## Config Reference (governance.json)

| Key | Purpose |
|-----|---------|
| `max_ideas_per_run` | Cap ideation volume (default: 5) |
| `max_debate_rounds` | Debate depth (default: 3) |
| `evidence_sources` | What to scan for evidence |
| `auto_approve` | Skip human gate (default: false) |
| `freeze_threshold` | Rejections before idea is frozen (default: 3) |
| `model_routing` | Which model for which phase |
| `frozen_ideas` | Ideas that should never be proposed again |
| `rejected_paths` | Ideas rejected with reasons (can be revisited with new evidence) |
| `active_directions` | Current improvement focus |
