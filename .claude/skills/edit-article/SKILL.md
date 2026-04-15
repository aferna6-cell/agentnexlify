---
name: edit-article
description: Restructure and tighten articles by cutting filler, sharpening arguments, and reordering sections. Use on knowledge-base/wiki/, blog drafts, marketing copy. Load when user says "edit this article", "tighten this", "restructure this post", "cut the fluff".
origin: https://github.com/mattpocock/skills/tree/main/edit-article
version: 1.0.0
triggers:
  - edit this article
  - tighten this
  - restructure this post
  - cut the fluff
  - sharpen this
  - improve this writing
---

# Edit Article — Structural Editing, Not Grammar

NOT proofreading. Restructures arguments, cuts filler, sharpens the point of each section. Default tone: Aidan voice (see `.claude/rules/personality.md`), not caveman (caveman is internal-only).

## When to Use
- Knowledge base wiki entry needs publish-quality edit
- Blog draft for marketing site
- README/docs that lost the thread
- Tenant-facing copy (landing page, in-app text)
- Long PRD/spec that's drifted into rambling

## When NOT to Use
- Pure grammar/typo pass (use a linter or `code-review` plugin)
- Code comments (use `comment-analyzer` agent)
- Internal-only chat output (caveman fine)
- Translation (out of scope)

## Editing passes (run in order)

### Pass 1 — Find the point
- Read whole article
- Write the SINGLE-SENTENCE thesis in the margin
- If the article doesn't have one → escalate to user
- If multiple competing points → pick one, defer rest

### Pass 2 — Restructure
- Move thesis to top (lead with the conclusion)
- Group supporting points by argument, not by chronology
- Cut sections that don't serve thesis
- Promote the strongest example to first
- Demote or cut weaker examples
- Section headers should preview the claim, not just label the topic
  - Bad: "Background"
  - Good: "Why GoHighLevel doesn't fit small contractors"

### Pass 3 — Sharpen
For each paragraph:
- Cut adjectives that don't carry weight
- Replace abstractions with concrete examples
- Replace hedges ("might", "perhaps", "could be argued") with assertions or admit you don't know
- Replace "leverage", "unlock", "synergy", "best-in-class", "robust", "seamless" — every time
- Replace passive with active voice when actor is known
- Cut the second sentence if first already made the point

### Pass 4 — Compress
- Target: 30-50% length reduction
- Combine paragraphs that share a point
- Remove transition phrases ("It's important to note that...")
- Bullet lists for parallel items
- Keep code blocks unchanged

### Pass 5 — Verify
- Does the lead still match the thesis after editing?
- Does each section earn its place?
- Read aloud — does it sound like Aidan or like LLM filler?
- Is every claim supported (link, number, example)?

## Output format
```markdown
# Edit Report — <article path>

## Thesis (extracted)
<single sentence>

## Structural changes
- Moved <section> to top because <reason>
- Cut <section> because <didn't serve thesis>
- Promoted <example> from bottom to lead

## Word count
- Before: <N>
- After: <M> (-<%>)

## Sharpening (samples)
- "leveraging robust AI capabilities" → "AI that works"
- "It might be argued that..." → "X is true because Y"

## Open questions for author
- <if any claim lacks evidence>
- <if thesis seems weak>

## Final draft
[full edited markdown]
```

## Voice rules (when editing FOR Aidan)
Per `.claude/rules/personality.md`:
- Direct, no-nonsense, evidence-first
- Avoids marketing speak and hype
- Concrete examples > abstractions
- Technical precision > politeness
- Owns conclusions, doesn't hedge
- Short sentences, short paragraphs
- Specific > vague, numbers > adjectives

## Anti-patterns to remove on sight
- "In today's fast-paced world..."
- "It's important to note that..."
- "At the end of the day..."
- "Game-changer", "unlock", "leverage", "seamless", "robust"
- "I think" / "I believe" → either assert or remove
- Rhetorical questions that pad
- Em-dash overuse — looks like AI

## Cross-refs
- `.claude/rules/personality.md` — voice rules
- `.claude/skills/wiki/SKILL.md` — wiki article publishing pipeline
- `.claude/skills/kb-lint/SKILL.md` — Karpathy template enforcement
- `PROMPTLIBRARY.md` — WRITE Marketing Copy prompt
