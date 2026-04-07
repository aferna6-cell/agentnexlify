---
title: "{Title — Concise, Specific, No Clickbait}"
category: {competitors|ai-llm|small-biz-saas|verticals|technical|regulations|growth|general}
tags: ["{tag1}", "{tag2}", "{tag3}"]
sources: ["{raw/category/source-file.md}"]
created: YYYY-MM-DD
updated: YYYY-MM-DD
challenged: YYYY-MM-DD   # added by /challenge-assumptions; omit until first run
summary: "{One sentence. What this article is about and why it matters. Must stand alone.}"
word_count: 0            # auto-filled by /wiki and /kb-compile
relevance_score: 8       # 1–10, how relevant to AgentNexLiFy
transcript_unavailable: false  # true only for YouTube articles without a transcript
---

# {Title}

{Opening paragraph: 3–5 sentences. Establish context, state the core thesis, explain why
this matters. Readers should know after this paragraph whether they need to read the rest.
No throat-clearing — start with the substance. This paragraph is the abstract. If a reader
reads only this, they should understand the core claim and its significance.}

{Body paragraph 1: clear topic sentence + development of one idea. Flows logically from
the opener. Dense with facts, data, and specific claims. Every sentence carries information.
No filler. Numbers over adjectives: "$300/mo" not "expensive", "3–5x higher" not "much higher".}

{Body paragraph 2: builds on or contrasts with paragraph 1. Reference other wiki articles
with [[slug]] syntax when another article covers a topic in depth. Don't cluster all links
in Related Articles — weave them into the prose.}

{Body paragraph 3: continue developing the argument or introduce a complicating factor.
Tables are appropriate for comparative data (feature matrices, pricing comparisons, scoring
rubrics). Use them instead of bullet lists when data has 2+ dimensions.}

{Body paragraph 4 (optional): technical detail, implementation consideration, or second-order
effects. Code blocks are appropriate in technical articles; use them sparingly elsewhere.}

{Body paragraph 5–7 (optional): additional evidence, edge cases, implications, open questions.
Aim for 3–7 total body paragraphs. Stop when the argument is complete, not when a word count
is hit. Acknowledge what you don't know in the final paragraph if relevant.}

## Key Concepts

{3–7 definitions. Only concepts specific to this article's domain that a reader might need
defined. Not a glossary of common terms — only concepts introduced or used in a domain-specific
way here. If a concept has its own wiki article, link it with [[slug]].}

- **{Concept Name}** — {1–2 sentence definition. Precise, not vague. Specific to how the
  concept is used in this article's context.}
- **{Concept Name}** — {Definition.}
- **{Concept Name}** — {Definition. If this concept has its own article: see [[concept-slug]].}

## Related Articles

{Every article must link to at least 1 other article. The link text explains the relationship —
it does not just name the article. This section is manually curated, not auto-generated.
It forces you to situate this article in the existing knowledge graph.}

- [[{slug-1}]] — {One sentence on how it relates to this article.}
- [[{slug-2}]] — {One sentence.}

## Relevance to AgentNexLiFy

{1–2 paragraphs. What does this knowledge mean for the product, the business, or the
engineering decisions? Be specific: "This means we should prioritize X over Y", or
"This validates our decision to build Z", or "This suggests a risk in our roadmap."
Every article must connect back to the product. Even purely academic or technical articles
must state how the knowledge applies. This is what makes the wiki a business asset rather
than a personal bookmarks folder.}

---

<!--
WRITING RULES (delete this block before saving):

TITLE: Specific and descriptive.
  Good: "GoHighLevel Competitor Profile"
  Bad: "Competitor Analysis"
  Good: "Prompt Caching — Cost and Latency Patterns"
  Bad: "Some Notes on Caching", "A Guide to Caching"
  Rules: No clickbait, no question titles, no "A Guide to X", no "Introduction to X"

SUMMARY: Exactly one sentence. Include the most important fact or conclusion. Someone
  scanning INDEX.md reads only this. "X causes Y because Z" beats "This article covers X."

BANNED PHRASES: Delete on sight.
  "It's worth noting that" | "Interestingly," | "It should be mentioned that"
  "As we can see," | "In conclusion," | "This article will explore"
  Just state the thing.

ESSAY NOT LISTICLE: Use bullet points only for genuinely list-like data (feature
  comparisons, pricing tables, numbered steps). Everything else is prose.

NUMBERS OVER ADJECTIVES:
  "$300/mo" not "expensive"
  "3–5x higher" not "much higher"
  "1M context window" not "very large context"
  "Deployed to 8 production tenants" not "widely used"

CROSS-REFERENCES: Use [[slug]] inline wherever another article covers a topic in depth.
  Don't cluster all links in Related Articles — weave them into the prose paragraphs.

SOURCE CLAIMS: Specific facts cite their source inline:
  "According to their 2026 pricing page..." or "(Referrizer 2025)"

OPINIONATED WHERE WARRANTED: "This matters because..." not just "This exists."
-->

---

# Example Article (Reference Quality — Delete Before Saving)

The following is a complete, filled-in example article using prompt caching as the topic.
It demonstrates the Karpathy format in practice: dense prose, inline cross-references,
specific numbers, actionable Relevance section.

```markdown
---
title: "Prompt Caching — Cost and Latency Patterns"
category: technical
tags: ["prompt-caching", "anthropic", "cost-optimization", "latency"]
sources: ["raw/technical/anthropic-prompt-caching-docs.md"]
created: 2026-04-06
updated: 2026-04-06
summary: "Anthropic's prompt caching reduces repeated-prefix costs by 90% and latency by 85%; AgentNexLiFy's widget chat is the ideal use case."
word_count: 620
relevance_score: 9
---

# Prompt Caching — Cost and Latency Patterns

Prompt caching allows reuse of previously processed prompt prefixes, avoiding redundant
computation on tokens that don't change between requests. Anthropic's implementation
(available on claude-sonnet-4-6 and claude-opus-4-6) caches the first N tokens of a prompt
and charges 1/10th the normal input price for cached tokens on subsequent requests. For
AgentNexLiFy's chat widget, where every message in a conversation resends the full system
prompt + conversation history, this represents the single largest cost optimization available.

The mechanics are straightforward: the API hashes the prompt prefix and checks for a cache
hit. If the first 2,048+ tokens of your prompt match a cached prefix, those tokens are served
from cache at 0.1x cost and ~85% lower latency. The cache has a 5-minute TTL that resets on
each hit, meaning active conversations keep the cache warm automatically. This aligns
perfectly with chat sessions, which typically see messages every 30–120 seconds.

The cost impact is substantial. AgentNexLiFy's widget system prompt is ~1,200 tokens. A
10-message conversation resends this prefix 10 times. Without caching, that's 12,000 input
tokens at full price. With caching, it's 1,200 at full price (first message) plus 10,800 at
0.1x — an 82% reduction in input token cost for that conversation. Across thousands of daily
conversations, this compounds into the difference between viable and unviable unit economics.

The latency improvement matters for perceived quality. Cached prefixes skip the prompt
processing phase entirely, reducing time-to-first-token from ~800ms to ~120ms on
claude-sonnet-4-6. For a chat widget where users expect instant responses, sub-200ms TTFT
feels like the bot is "ready and waiting" rather than "thinking." This is the kind of
performance difference that affects whether a user trusts the AI or abandons the conversation.

Implementation requires ordering the prompt so that stable content comes first: system prompt,
then business context (FAQ, business hours, service types), then conversation history. The
conversation history is the part that changes, so it must come last. AgentNexLiFy already
structures prompts this way in `backend/services/chat_service.py`, making adoption
straightforward. The only change needed is adding `cache_control` markers to the message
array, as documented in [[claude-api-patterns]].

One caveat: caching works per-model, per-organization. If AgentNexLiFy switches between
models mid-conversation (e.g., using claude-haiku-4-5-20251001 for simple queries and
claude-sonnet-4-6 for complex ones), each model maintains a separate cache. The routing
logic in [[model-routing]] should account for this — switching models mid-conversation loses
the cache benefit.

## Key Concepts

- **Cache TTL** — Time-to-live for cached prompt prefixes. Anthropic's default is 5 minutes,
  resetting on each cache hit. Active conversations keep it warm; abandoned ones expire
  naturally.
- **Prefix matching** — Caching requires the prompt prefix to match exactly, byte-for-byte.
  Any change to the system prompt (even whitespace) invalidates the cache for all active
  conversations.
- **TTFT (Time to First Token)** — The latency between sending a request and receiving the
  first token of the response. The primary user-perceived latency metric for streaming
  responses.
- **Cache-aware prompt ordering** — Structuring prompts so that stable content (system
  prompt, context) comes before variable content (conversation history, user message).
  Required for effective caching.

## Related Articles

- [[claude-api-patterns]] — Implementation details for cache_control markers in the
  Anthropic SDK.
- [[model-routing]] — How AgentNexLiFy routes between Claude models; caching implications
  for mid-conversation switches.
- [[widget-performance]] — End-to-end latency budget for the chat widget, where TTFT is the
  dominant factor.

## Relevance to AgentNexLiFy

Prompt caching should be the next cost optimization implemented. The widget chat use case
(repeated system prompt + growing conversation history) is the textbook example of where
caching delivers maximum ROI. At current volumes (~2,000 conversations/day across all
tenants), the estimated monthly savings are $400–600 on API costs alone, with the TTFT
improvement as a free bonus. Implementation is a 2-hour task: add cache_control markers to
the system prompt block in `backend/services/chat_service.py` and verify with the Anthropic
usage dashboard that cache hit rates exceed 80%.
```
