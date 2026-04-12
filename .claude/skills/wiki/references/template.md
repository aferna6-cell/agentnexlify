## Template Reference (VERBATIM — Karpathy Article Format)

Every article produced by `/wiki` must follow this template exactly. Do not deviate.

```markdown
---
title: "{Title — Concise, Specific, No Clickbait}"
category: {category}
tags: [{tag1}, {tag2}, {tag3}]
sources: ["{raw/category/source-file.md}"]
created: YYYY-MM-DD
updated: YYYY-MM-DD
summary: "{One sentence. What this article is about and why it matters.}"
---

# {Title}

{Opening paragraph: 3-5 sentences that establish context, state the core thesis,
and explain why this matters. The reader should know after this paragraph whether
they need to read the rest. No throat-clearing — start with the substance.}

{Body paragraphs: 3-7 paragraphs of essay-style prose. Each paragraph has a clear
topic sentence and develops one idea. Paragraphs flow logically — each one builds
on or contrasts with the previous. Dense with facts, data, and specific claims.
Every sentence carries information; no filler.

Cross-reference other wiki articles using [[slug]] syntax wherever a concept is
covered in more depth elsewhere. Example: "As documented in [[competitive-landscape-march-2026]],
the market has shifted toward..." These links create the knowledge graph.

Tables are appropriate for comparative data (feature matrices, pricing comparisons,
scoring rubrics). Use them instead of bullet lists when the data has 2+ dimensions.

Code blocks are appropriate for technical articles showing patterns, configurations,
or SQL. Use them sparingly in non-technical articles.

Specific numbers beat vague claims. "Podium charges $300-600/mo" not "Podium is expensive."
"SMS gets 3-5x higher response rates than email (Referrizer 2025)" not "SMS works better."}

## Key Concepts

{3-7 concept definitions. Each is a term or idea introduced or referenced in the article
that a reader might not know or might need a precise definition for. Not a glossary of
common terms — only concepts that are specific to this article's domain.}

- **{Concept Name}** — {1-2 sentence definition. Precise, not vague. If this concept
  has its own wiki article, link it: see [[concept-slug]].}
- **{Concept Name}** — {Definition.}
- **{Concept Name}** — {Definition.}

## Related Articles

{Links to other wiki articles that are thematically related, provide supporting evidence,
offer contrasting viewpoints, or cover prerequisite concepts. This section is the explicit
cross-reference map for this article.}

- [[{slug-1}]] — {One sentence on how it relates to this article.}
- [[{slug-2}]] — {One sentence.}
- [[{slug-3}]] — {One sentence.}

## Relevance to AgentNexLiFy

{1-2 paragraphs. What does this knowledge mean for the product, the business, or the
engineering decisions? This section transforms abstract knowledge into actionable insight.
Be specific: "This means we should prioritize X over Y" or "This validates our decision
to build Z" or "This suggests a risk we haven't accounted for in our roadmap."}
```

### Template Rules (Hard Constraints)

1. **Title** — Specific and descriptive. "GoHighLevel Competitor Profile" not "Competitor Analysis." No clickbait, no question titles, no "A Guide to X." No "Notes on X."

2. **Summary** — Exactly one sentence in the frontmatter. Must stand alone — someone scanning INDEX.md reads only this. Must include the most important fact or conclusion, not a topic description.

3. **Opening Paragraph** — The first paragraph is the abstract. If a reader reads only this, they should understand the core claim and its significance. Start with substance.

4. **Body** — Essay-style prose, not bullet lists. Paragraphs, not headers-with-bullets. Tables only for genuinely tabular data. Tone: "knowledgeable colleague explaining to another knowledgeable colleague."

5. **Key Concepts** — Not a general glossary. Only concepts specific to this article's domain that a reader might need defined. 3-7 concepts. Link to existing articles where applicable.

6. **Related Articles** — Every article must link to at least 1 other article. The link text must explain the relationship, not just name the article.

7. **Relevance to AgentNexLiFy** — Mandatory in every article. Even purely academic articles must state how the knowledge applies to the product or business decisions.

8. **Cross-references** — Use `[[slug]]` syntax inline throughout the body prose wherever another article covers a topic in more depth. Don't cluster all links in Related Articles.

9. **No filler phrases.** Banned: "It's worth noting that", "Interestingly,", "It should be mentioned that", "As we can see,", "In conclusion,". State the thing directly.

10. **Numbers over adjectives.** "$300/mo" not "expensive." "3-5x higher" not "much higher." Cite sources for statistics when available.

---

## Example Article (Reference Quality)

The following article demonstrates the correct output format and prose quality. Use it as a benchmark.

```markdown
---
title: "Prompt Caching — Cost and Latency Patterns"
category: technical
tags: ["prompt-caching", "anthropic", "cost-optimization", "latency"]
sources: ["raw/technical/anthropic-prompt-caching-docs.md"]
created: 2026-04-06
updated: 2026-04-06
summary: "Anthropic's prompt caching reduces repeated-prefix costs by 90% and latency by 85%; AgentNexLiFy's widget chat is the ideal use case."
---

# Prompt Caching — Cost and Latency Patterns

Prompt caching allows reuse of previously processed prompt prefixes, avoiding
redundant computation on tokens that don't change between requests. Anthropic's
implementation (available on claude-sonnet-4-6 and claude-opus-4-6) caches the
first N tokens of a prompt and charges 1/10th the normal input price for cached
tokens on subsequent requests. For AgentNexLiFy's chat widget, where every message
in a conversation resends the full system prompt + conversation history, this
represents the single largest cost optimization available.

The mechanics are straightforward: the API hashes the prompt prefix and checks
for a cache hit. If the first 2,048+ tokens of your prompt match a cached prefix,
those tokens are served from cache at 0.1x cost and ~85% lower latency. The cache
has a 5-minute TTL that resets on each hit, meaning active conversations keep the
cache warm automatically. This aligns perfectly with chat sessions, which typically
see messages every 30-120 seconds.

The cost impact is substantial. AgentNexLiFy's widget system prompt is ~1,200
tokens. A 10-message conversation resends this prefix 10 times. Without caching,
that's 12,000 input tokens at full price. With caching, it's 1,200 at full price
(first message) plus 10,800 at 0.1x — a 82% reduction in input token cost for
that conversation. Across thousands of daily conversations, this compounds into
the difference between viable and unviable unit economics.

The latency improvement matters for perceived quality. Cached prefixes skip the
prompt processing phase entirely, reducing time-to-first-token from ~800ms to
~120ms on claude-sonnet-4-6. For a chat widget where users expect instant
responses, sub-200ms TTFT feels like the bot is "ready and waiting" rather than
"thinking." This is the kind of performance difference that affects whether a
user trusts the AI or abandons the conversation.

Implementation requires ordering the prompt so that stable content comes first:
system prompt, then business context (FAQ, business hours, service types), then
conversation history. The conversation history is the part that changes, so it
must come last. AgentNexLiFy already structures prompts this way in
`backend/services/chat_service.py`, making adoption straightforward. The only
change needed is adding `cache_control` markers to the message array, as
documented in [[claude-api-patterns]].

One caveat: caching works per-model, per-organization. If AgentNexLiFy switches
between models mid-conversation (e.g., using claude-haiku-4-5-20251001 for simple
queries and claude-sonnet-4-6 for complex ones), each model maintains a separate
cache. The routing logic in [[model-routing]] should account for this — switching
models mid-conversation loses the cache benefit.

## Key Concepts

- **Cache TTL** — Time-to-live for cached prompt prefixes. Anthropic's default is
  5 minutes, resetting on each cache hit. Active conversations keep it warm;
  abandoned ones expire naturally.
- **Prefix matching** — Caching requires the prompt prefix to match exactly,
  byte-for-byte. Any change to the system prompt (even whitespace) invalidates
  the cache for all active conversations.
- **TTFT (Time to First Token)** — The latency between sending a request and
  receiving the first token of the response. The primary user-perceived latency
  metric for streaming responses.
- **Cache-aware prompt ordering** — Structuring prompts so that stable content
  (system prompt, context) comes before variable content (conversation history,
  user message). Required for effective caching.

## Related Articles

- [[claude-api-patterns]] — Implementation details for cache_control markers in
  the Anthropic SDK.
- [[model-routing]] — How AgentNexLiFy routes between Claude models; caching
  implications for mid-conversation switches.
- [[widget-performance]] — End-to-end latency budget for the chat widget, where
  TTFT is the dominant factor.

## Relevance to AgentNexLiFy

Prompt caching should be the next cost optimization implemented. The widget chat
use case (repeated system prompt + growing conversation history) is the textbook
example of where caching delivers maximum ROI. At current volumes (~2,000
conversations/day across all tenants), the estimated monthly savings are $400-600
on API costs alone, with the TTFT improvement as a free bonus. Implementation is
a 2-hour task: add cache_control markers to the system prompt block in
chat_service.py and verify with the Anthropic usage dashboard that cache hit
rates exceed 80%.
```
