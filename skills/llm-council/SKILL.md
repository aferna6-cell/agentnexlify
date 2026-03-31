# LLM Council

Run any question, idea, or decision through a council of 5 AI advisors who independently analyze it, peer-review each other anonymously, and synthesize a final verdict. Based on Karpathy's LLM Council methodology.

## Triggers

**Mandatory:** "council this", "run the council", "war room this", "pressure-test this", "stress-test this", "debate this"

**Strong (when combined with a real decision or tradeoff):** "should I X or Y", "which option", "what would you do", "is this the right move", "validate this", "get multiple perspectives", "I can't decide", "I'm torn between"

**Do NOT trigger on:** simple yes/no questions, factual lookups, or casual "should I" without a meaningful tradeoff.

## When to Run the Council

The council is for questions where being wrong is expensive.

Good council questions:
- "Should I launch a $97 workshop or a $497 course?"
- "Which of these 3 positioning angles is strongest?"
- "I'm thinking of pivoting from X to Y. Am I crazy?"
- "Here's my landing page copy. What's weak?"
- "Should I hire a VA or build an automation first?"

Bad council questions:
- "What's the capital of France?" (one right answer)
- "Write me a tweet" (creation task, not a decision)
- "Summarize this article" (processing task, not judgment)

## The Five Advisors

Each advisor is a thinking style, not a persona. They create natural tension.

### 1. The Contrarian
Actively looks for what's wrong, what's missing, what will fail. Assumes the idea has a fatal flaw and tries to find it. Not a pessimist — the friend who saves you from a bad deal by asking the questions you're avoiding.

### 2. The First Principles Thinker
Ignores the surface-level question and asks "what are we actually trying to solve here?" Strips away assumptions. Rebuilds the problem from the ground up. Sometimes the most valuable output is "you're asking the wrong question entirely."

### 3. The Expansionist
Looks for upside everyone else is missing. What could be bigger? What adjacent opportunity is hiding? Doesn't care about risk (that's the Contrarian's job). Cares about what happens if this works even better than expected.

### 4. The Outsider
Has zero context about you, your field, or your history. Responds purely to what's in front of them. Catches the curse of knowledge: things that are obvious to you but confusing to everyone else.

### 5. The Executor
Only cares about: can this actually be done, and what's the fastest path? Ignores theory and big-picture thinking. Looks at every idea through the lens of "OK but what do you do Monday morning?"

**Why these five:** Three natural tensions. Contrarian vs Expansionist (downside vs upside). First Principles vs Executor (rethink everything vs just do it). Outsider sits in the middle keeping everyone honest.

## How a Council Session Works

### Step 1: Frame the Question (with Context Enrichment)

Before framing, scan the workspace for context:
- `CLAUDE.md` in the project root (business context, preferences, constraints)
- Memory files in `.auto-memory/` (audience profiles, business details, past decisions)
- Any files the user explicitly referenced or attached
- Recent council transcripts in `/skills/llm-council/transcripts/` (to avoid re-counciling the same ground)

Then frame the question as a clear, neutral prompt including:
1. The core decision or question
2. Key context from the user's message
3. Key context from workspace files
4. What's at stake

### Step 2: Convene the Council (5 Sub-Agents in Parallel)

Spawn all 5 advisors simultaneously as sub-agents. Each gets:
1. Their advisor identity and thinking style
2. The framed question
3. Instruction: respond independently. Do not hedge. Lean fully into your assigned perspective. 150-300 words. No preamble.

**Sub-agent prompt template:**

```
You are [Advisor Name] on an LLM Council.

Your thinking style: [advisor description]

A user has brought this question to the council:

---
[framed question]
---

Respond from your perspective. Be direct and specific. Don't hedge or try to be balanced. Lean fully into your assigned angle. The other advisors will cover the angles you're not covering.

Keep your response between 150-300 words. No preamble. Go straight into your analysis.
```

### Step 3: Peer Review (5 Sub-Agents in Parallel)

Collect all 5 responses. Anonymize as Response A through E (randomize mapping). Spawn 5 new sub-agents. Each reviewer answers:
1. Which response is the strongest and why?
2. Which response has the biggest blind spot?
3. What did ALL responses miss?

**Reviewer prompt template:**

```
You are reviewing the outputs of an LLM Council. Five advisors independently answered this question:

---
[framed question]
---

Here are their anonymized responses:

**Response A:** [response]
**Response B:** [response]
**Response C:** [response]
**Response D:** [response]
**Response E:** [response]

Answer these three questions. Be specific. Reference responses by letter.

1. Which response is the strongest? Why?
2. Which response has the biggest blind spot? What is it missing?
3. What did ALL five responses miss that the council should consider?

Keep your review under 200 words. Be direct.
```

### Step 4: Chairman Synthesis

One agent gets everything: original question, all 5 responses (de-anonymized), and all 5 peer reviews.

**Chairman output structure:**

```
## Where the Council Agrees
[Points multiple advisors converged on independently. High-confidence signals.]

## Where the Council Clashes
[Genuine disagreements. Present both sides. Explain why reasonable advisors disagree.]

## Blind Spots the Council Caught
[Things that only emerged through peer review.]

## The Recommendation
[A clear, direct recommendation. Not "it depends." A real answer with reasoning.]

## The One Thing to Do First
[A single concrete next step. Not a list. One thing.]
```

### Step 5: Generate the Council Report

Create a visual HTML report: `council-report-[YYYY-MM-DD-HHMMSS].html`

Single self-contained HTML file with inline CSS. Clean design. Contains:
1. The question at the top
2. The chairman's verdict prominently displayed
3. Agreement/disagreement visual (grid or spectrum showing advisor positions)
4. Collapsible sections for each advisor's full response (collapsed by default)
5. Collapsible section for peer review highlights
6. Footer with timestamp

Style: white background, subtle borders, system font stack, soft accent colors per advisor. Professional briefing document look.

Save to `/skills/llm-council/reports/`

### Step 6: Save the Full Transcript

Save as `council-transcript-[YYYY-MM-DD-HHMMSS].md` in `/skills/llm-council/transcripts/`

Includes: original question, framed question, all 5 advisor responses, all 5 peer reviews (with anonymization mapping revealed), chairman's full synthesis.

## Important Rules

- ALWAYS spawn all 5 advisors in parallel. Sequential spawning wastes time and lets earlier responses bleed into later ones.
- ALWAYS anonymize for peer review. If reviewers know which advisor said what, they defer to certain thinking styles instead of evaluating on merit.
- The chairman CAN disagree with the majority if the reasoning supports it.
- Don't council trivial questions. If there's one right answer, just answer it.
- The visual report matters. Most users scan the report, not the transcript. Make the HTML clean and scannable.
