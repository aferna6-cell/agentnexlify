---
title: "LLM Wiki — Karpathy's Compounding Knowledge Base Pattern"
slug: ai-llm/llm-wiki-karpathy-pattern
category: ai-llm
tags: [knowledge-management, rag, llm-wiki, karpathy, compounding-knowledge, obsidian, embeddings]
summary: "LLM Wiki replaces RAG's ephemeral retrieval with a persistent, self-maintaining wiki where every new source updates multiple interconnected entity pages simultaneously, causing knowledge to compound rather than restart."
sources:
  - "https://github.com/karpathy/llm-wiki"
  - "https://x.com/karpathy/status/llm-wiki-announcement"
created: 2026-04-06
updated: 2026-04-06
word_count: 920
transcript_unavailable: false
relevance_score: 10
---

# LLM Wiki — Karpathy's Compounding Knowledge Base Pattern

The fundamental failure mode of RAG (Retrieval-Augmented Generation) is that it re-derives knowledge on every query. You ask a question, the system searches a document corpus, retrieves fragments, patches them together into an answer, and then discards all of that work. The next question starts from scratch. LLM Wiki, released by Andrej Karpathy in April 2026 (5,000 GitHub stars in 48 hours, 1,294 forks), proposes a different model: instead of retrieval on demand, maintain a persistent wiki that an LLM continuously reads, updates, and cross-links. Knowledge compounds. Nothing disappears into chat history.

The mechanics are intentionally simple. You maintain a directory of markdown files organized by entity or concept. When a new source arrives — an article, a paper, a meeting transcript, a Slack thread — the LLM reads both the source and every potentially relevant wiki page, then writes updates. A single source can touch 10–15 wiki pages simultaneously: the main entity page gets updated facts, related concept pages get cross-references, a contradictions page gets flagged if the new source conflicts with existing content, and the index is rebuilt. This is fundamentally different from vector search, which retrieves passages but never synthesizes them back into the canonical knowledge store.

The compounding effect is the key insight. In a RAG system, ingesting your 100th document is no harder for the system than ingesting the first — each query still searches across all documents independently. In LLM Wiki, your 100th article lands in a wiki that already understands context from the previous 99. The LLM can write richer entity pages, make more precise cross-references, and identify contradictions because it has accumulated context. The wiki gets smarter with each addition, not just larger.

Karpathy describes four use cases that illuminate the pattern's range. For personal knowledge, you file journal entries and health data into a structured wiki about yourself — it builds a picture of your psychology, habits, and goals that evolves over time rather than living in disconnected notes. For research, you read papers for months and the wiki builds a comprehensive synthesis with an evolving thesis, automatically flagging where new papers agree or contradict the current state of understanding. For reading fiction, you build a fan wiki as you read — characters, themes, plot threads, all cross-referenced — so you can ask questions like "what has this character said about X" and get an answer that draws on the entire wiki rather than a passage search. For business, you feed Slack threads, meeting transcripts, and customer calls into a wiki that stays current because the LLM does the maintenance work that nobody wants to do manually.

The contrast with NotebookLM, ChatGPT file uploads, and most commercial RAG systems is architectural. Those systems treat documents as a static corpus to search. LLM Wiki treats documents as inputs to a knowledge compilation process whose output is a maintained encyclopedia. The analogy Karpathy uses is apt: Obsidian is the IDE, the LLM is the programmer, the wiki is the codebase. You never write the wiki yourself. You source, explore, and ask questions. The LLM does all the grunt work. This framing explains why the pattern works: LLMs are good at structured writing and synthesis, which is exactly what wiki maintenance requires.

The practical implications for building AI-powered systems are significant. Systems that need to answer questions across a large, evolving body of knowledge — customer support bots, research assistants, competitive intelligence tools — benefit from maintaining a compiled knowledge base rather than running retrieval on every query. The compilation step is expensive, but it happens once per source addition, not once per query. At query time, you're reading from a pre-synthesized wiki, which is both faster and more coherent than on-the-fly fragment assembly.

## Key Concepts

**Compounding knowledge** — Each new source makes the entire knowledge base smarter, not just larger. Later sources are contextualized against earlier ones, enabling richer synthesis and contradiction detection.

**Entity pages** — The atomic unit of LLM Wiki. Each important concept, person, company, or theme gets its own page that is read and updated when relevant new sources arrive. Pages accumulate sources, not just content.

**Contradiction flagging** — When a new source conflicts with existing wiki content, the LLM flags the conflict rather than silently overwriting. This makes the evolution of knowledge explicit and auditable.

**One-to-many source propagation** — A single input document updates multiple wiki pages simultaneously. This is the mechanism behind compounding: a paper about transformer efficiency might update the transformers page, the attention mechanism page, the inference optimization page, and the hardware requirements page all at once.

**Wiki-grounded Q&A** — Answers to queries are generated from the wiki, not from the source documents directly. High-quality answers get filed back as new wiki pages, so exploration itself compounds the knowledge base.

## Related Articles

- [[competitive-landscape-march-2026]] — GoHighLevel and competitors are building RAG-based chat systems; LLM Wiki pattern could differentiate AgentNexLiFy's knowledge layer
- [[post-launch-growth-strategy]] — Customer onboarding wiki that auto-updates from support tickets is a direct application of this pattern

## Relevance to AgentNexLiFy

AgentNexLiFy's existing KB pipeline (kb-ingest → kb-compile → kb-query) already approximates the LLM Wiki pattern: sources are compiled into wiki articles and queried via embeddings. The gap is the **update propagation** mechanism — when a new article is ingested, existing related articles are not automatically revised to incorporate the new information. Implementing full LLM Wiki semantics would mean that `/wiki` triggers not just article creation but a sweep of related articles to check for necessary updates. This is expensive but transforms the KB from an additive archive into a true compounding knowledge base. At 10+ articles per category, the compounding effect begins to produce qualitatively different Q&A quality than RAG on the raw sources. The [[challenge-assumptions]] cron is a partial implementation of this — it runs the LLM against existing articles to generate updates — but full LLM Wiki would also propagate new source content into existing articles.
