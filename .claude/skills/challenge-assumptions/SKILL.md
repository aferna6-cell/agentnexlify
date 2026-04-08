---
name: challenge-assumptions
description: "Generate steelman counterarguments for recent wiki articles. Prevents echo-chamber thinking by challenging assumptions in the knowledge base."
version: 1.0.0
origin: claude
user_invocable: true
allowed_tools: []
triggers: ["/challenge-assumptions", "challenge assumptions", "assumption review", "challenge wiki"]
effort: medium
---

# challenge-assumptions

Question every belief in the knowledge base. Read recent wiki articles and generate steelman
counterarguments, alternative explanations, and blind spots for each one. Appends a
`## Challenges` section to each article so the pushback lives next to the original claim.

## Usage

```
/challenge-assumptions              # challenge articles updated in last 7 days (default)
/challenge-assumptions --days 30    # override window to 30 days
/challenge-assumptions --article wiki/competitors/gohighlevel.md  # challenge a single article
```

Can also be triggered by cron via `scripts/daily/challenge-assumptions.sh`.

## When NOT to Use
- The knowledge base is brand new with no articles to challenge yet
- During active brainstorming sessions where you want to generate ideas without pushback
- When the user wants a quick answer and not a thorough debate
- For articles that are purely technical reference (no claims to challenge)

---

## Workflow

### Step 1: Select Target Articles

**Single article mode** (`--article` flag):
- Read the file at the provided path directly.
- Use just that one article. Skip to Step 2.

**Batch mode** (no `--article` flag):
- Read `knowledge-base/INDEX.md` to get the full article list.
- Parse `--days N` argument (default: 7).
- For each article listed, read the file and inspect its frontmatter.
- Filter to articles where `created` OR `updated` falls within the last N days
  (compare against today's date).
- **Skip** any article that already has a `## Challenges` section anywhere in its body.
  Rationale: challenges are appended once; to re-challenge, delete the section manually.

If no articles pass the filter, report:
```
No articles to challenge (0 articles updated in the last N days, or all already challenged).
```
and stop.

### Step 2: Generate Challenges (per article)

For EACH selected article, read the full content and generate **3–5 challenges**.

Each challenge must be one of three types:

| Type | Label | Description |
|------|-------|-------------|
| Counterargument | `[Counterargument]` | A reasonable person could argue the opposite of the article's central claim. |
| Alternative Explanation | `[Alternative Explanation]` | The same data or evidence cited in the article could support a different conclusion. |
| Blind Spot | `[Blind Spot]` | Something the article doesn't consider that could materially change the conclusion. |

**Quality standards — each challenge must be:**

1. **Specific** — Reference an exact claim, statistic, or argument from the article.
   Bad: "But what if you're wrong about competitors?"
   Good: "This article claims GoHighLevel's $297/mo AI Employee plan is priced too high for SMBs,
   but US SMBs already spend $400-800/mo on answering services (Ruby Receptionists, Smith.ai),
   making that price point competitive rather than prohibitive."

2. **Steelmanned** — Present the strongest possible version of the counterposition.
   Do not strawman. Assume the challenger is intelligent and has access to the same data.

3. **Actionable** — State what evidence or research would resolve the question.
   Every challenge ends with: "Evidence needed to resolve: [specific thing to check]."

**Guideline on challenge types per article:**
- For opinion/analysis articles: 2 counterarguments, 1–2 alternative explanations, 1 blind spot.
- For factual/technical articles: 1 counterargument, 1 alternative explanation, 2–3 blind spots.
- Adjust based on article content — don't force a distribution if it doesn't fit.

### Step 3: Append Challenges Section to Each Article

Locate the insertion point in the article body:

1. If a `## Relevance to AgentNexLiFy` section exists, insert the `## Challenges` section
   **immediately before** it.
2. Otherwise, append the `## Challenges` section at the very end of the file.

Append in this exact format:

```markdown
## Challenges

_Generated YYYY-MM-DD by assumption review._

1. **[Counterargument] Title of the challenge.** The article claims [specific claim].
   A counterargument: [steelmanned opposing position]. This matters because [why it would
   change the conclusion].
   Evidence needed to resolve: [specific dataset, experiment, or source that would settle this].

2. **[Blind Spot] Title.** This analysis doesn't account for [X]. [Explanation of
   what X is and how it could change the conclusion if it were true.]
   Evidence needed to resolve: [what to check].

3. **[Alternative Explanation] Title.** The evidence cited ([specific evidence]) equally
   supports [alternative interpretation]. [Why this interpretation is plausible.]
   Evidence needed to resolve: [what to check].
```

Use real challenge count (3–5). Use today's date for `YYYY-MM-DD`.

### Step 4: Update Frontmatter

For each article that received challenges, update its YAML frontmatter:

1. Add `challenged: YYYY-MM-DD` (today's date) if not present. If already present,
   update to today's date.
2. Bump `updated: YYYY-MM-DD` to today's date.

Read the current frontmatter, modify it in memory, and write the file with the updated
frontmatter at the top.

**Do not modify any other part of the article body during this step** — only the frontmatter
block (between the `---` delimiters at the top).

### Step 5: Report

After processing all articles, output a summary table:

```
## Assumption Challenges — YYYY-MM-DD

Articles challenged: N
Total challenges generated: M

| Article | Path | Challenges | Types |
|---------|------|------------|-------|
| {Title} | wiki/{category}/{slug}.md | 4 | 2 counter, 1 blind spot, 1 alt explanation |
| {Title} | wiki/{category}/{slug}.md | 3 | 1 counter, 2 blind spots |
```

If running in single-article mode, also print the full generated challenges text to the
terminal so the user can review them immediately.

---

## Design Decisions

- **Challenges live in the article, not separately.** When you re-read an article in the
  future, you see the pushback immediately next to the original claims. This is the whole
  point — challenges in a separate file are easy to ignore.

- **Skip already-challenged articles.** The workflow runs daily via cron; re-challenging
  the same article every day would produce redundant noise. Manual re-challenge is possible
  by deleting the `## Challenges` section.

- **3–5 challenges only.** More is noise. Fewer isn't useful. The goal is targeted,
  high-quality challenges, not exhaustive lists.

- **Steelman, not strawman.** Weak objections are useless. Every challenge must represent
  the strongest possible opposing position.

- **Cron at 9 PM, after evening routine at 8 PM.** The evening routine may create or update
  articles. The challenge cron processes the latest state.

- **`--days N` default is 7.** Weekly cadence matches a realistic article creation rate.
  For a knowledge base with many recent articles, increase with `--days 30`.

---

## Scheduling

### crontab

```cron
0 21 * * * /home/aidan/agentnexlify/scripts/daily/challenge-assumptions.sh
```

### Windows Task Scheduler (WSL)

- **Task name:** `AgentNexLiFy-ChallengeAssumptions`
- **Schedule:** Daily at 9:00 PM
- **Action:** `wsl.exe bash /home/aidan/agentnexlify/scripts/daily/challenge-assumptions.sh`

See `scripts/daily/setup-scheduler.ps1` and `scripts/daily/setup-cron.sh` for the existing
scheduling infrastructure this plugs into.
