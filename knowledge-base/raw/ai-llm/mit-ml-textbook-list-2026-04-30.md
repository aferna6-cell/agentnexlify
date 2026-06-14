# MIT-Adjacent ML Textbooks — Free Primary-Source Reading List

Source: damidefi crypto-Twitter thread (2026-04-30). Stripped hype, kept book list.

## Useful kernel
12 graduate-level ML textbooks, all free + legitimately authored. Useful as personal reading reference. Article framing claimed Project upload turns Claude into a "first-principles reasoning substrate" — that claim is overstated (Projects use chunked retrieval, not full-context reasoning; 12 books exceed any context window). Discount the magic-Project narrative.

## Pattern note
Our existing `knowledge-base/wiki/` (101 articles, pgvector embeddings, Karpathy LLM Wiki pattern) already implements the curated-knowledge-substrate idea better than raw textbook upload. Distilled wiki entries beat raw books for retrieval quality.

## Book list (verified canonical, free)

### Foundations
- **Foundations of Machine Learning** — Mohri, Rostamizadeh, Talwalkar — http://mlbook.cs.nyu.edu
- **Understanding Deep Learning** — Simon J.D. Prince — https://udlbook.github.io/udlbook
- **Machine Learning Systems** (MIT curriculum) — https://mlsysbook.ai

### Advanced techniques
- **Algorithms for Decision Making** — Kochenderfer, Wheeler, Wray — https://algorithmsbook.com
- **Deep Learning** — Goodfellow, Bengio, Courville — https://www.deeplearningbook.org

### Reinforcement learning
- **Reinforcement Learning: An Introduction** — Sutton & Barto — http://incompleteideas.net/book/the-book.html
- **Distributional Reinforcement Learning** — Bellemare et al. — https://www.distributional-rl.org
- **Multi-Agent Reinforcement Learning** — Albrecht, Christianos, Schäfer — https://marl-book.com
- **Decision Making (Long Game)** — Kochenderfer — https://mykel.kochenderfer.com/textbooks

### Ethics + probability
- **Fairness and Machine Learning** — Barocas, Hardt, Narayanan — https://fairmlbook.org
- **Probabilistic Machine Learning: Introduction** (vol 1) — Kevin Murphy — https://probml.github.io/book1.html
- **Probabilistic Machine Learning: Advanced Topics** (vol 2) — Kevin Murphy — https://probml.github.io/book2.html

## Recommended top-3 (highest signal per page)
1. Murphy probml vol 1 — probability-grounded ML intro
2. Sutton & Barto — RL canonical, foundation for agent reasoning
3. Prince UDL — clearest deep-learning explanation in print

## What NOT to do
- Do not upload all 12 to a Claude Project expecting "reasoning substrate" magic. RAG retrieval ≠ persistent reasoning.
- Do not treat author's Kelly-Criterion-fat-tail anecdote as proof — Claude knows that from base training.
- Do not follow "@damidefi journey to 100K" engagement-bait tail.

## When this matters for AgentNexLiFy
- Not load-bearing. SaaS engineering, not quant ML research.
- Useful only if Aidan wants ML depth for personal reading.
- Existing KB pattern (wiki/) already covers the practical "ground Claude in curated knowledge" workflow.

## Cross-refs
- `.claude/rules/kb-first.md` — knowledge-base-first rule
- `knowledge-base/wiki/ai-llm/llm-wiki-karpathy-pattern.md` — distilled-wiki pattern
- `knowledge-base/raw/ai-llm/notebooklm-terminal-pattern-2026-04-29.md` — adjacent pattern (terminal-based note ingestion)
