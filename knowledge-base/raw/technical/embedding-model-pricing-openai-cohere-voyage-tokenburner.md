---
source_url: https://www.tokenburner.dev/insights/embedding-model-pricing-comparison
fetched_at: 2026-04-27T22:15:12Z
category: technical
title: 'Embedding Model Pricing: OpenAI, Cohere, Voyage Cost Comparison'
---

# Embedding Model Pricing: OpenAI, Cohere, Voyage Cost Comparison

#
TL;DR
OpenAI text-embedding-3-small: $0.02/1M tokens (cheapest for volume)
Voyage and Cohere often beat OpenAI on quality-per-dollar for retrieval
Embedding cost is usually 5–15% of total RAG bill; don't over-optimize at the expense of retrieval quality
Batch embedding jobs: use async APIs or local models (sentence-transformers) for one-time backfills
#
Who This Is For
Teams building RAG or semantic search. You're indexing 100K+ documents and want to understand embedding costs before committing to a provider.
#
Assumptions & Inputs
Index size: 100K–5M chunks
Chunk size: 256–512 tokens average
Re-index frequency: weekly or on document change
Need: good retrieval quality + predictable cost
#
The Embedding Bill Nobody Talks About
Your RAG stack has three cost layers:
embeddings
(one-time per chunk),
vector DB
(storage + queries), and
LLM
(generation). Most posts focus on the LLM. But at 1M chunks, embedding once at $0.10/1M tokens is
$100
—and if you re-embed on every doc update, that number grows.
Here’s how the major providers stack up (representative 2026 pricing; verify on their sites).
#
Provider Comparison (per 1M tokens, input)
Provider
Model
Price/1M
Dimensions
Notes
OpenAI
text-embedding-3-small
$0.02
1536
Cheapest, good for high volume
OpenAI
text-embedding-3-large
$0.13
3072
Higher quality, 6.5x cost
Cohere
embed-v3 (english)
~$0.10
1024
Strong retrieval benchmarks
Voyage
voyage-3
~$0.06
1024+
Tuned for RAG, good quality/cost
Google
text-embedding-004
~$0.025
768
Competitive with small models
Takeaway:
For pure cost at scale,
text-embedding-3-small
wins. For better retrieval with a reasonable bump,
Voyage
or
Cohere
often give better relevance per dollar.
#
When to Care About Embedding Cost
Large one-time backfills
(millions of chunks): small per-token differences add up; consider batch pricing and local models for backfill.
Frequent re-indexing:
every re-embed multiplies cost; optimize chunking and incremental updates.
Low budget, high quality need:
invest in a better embedding model (Voyage/Cohere) rather than stuffing more chunks into a cheap one.
#
When Not to Obsess
Small indexes (under 100K chunks):
embedding cost is in the tens of dollars; focus on retrieval quality and LLM cost.
Stable index, rare updates:
one-time cost; pick for quality, not pennies.
#
Practical Tips
Batch everything.
Use providers’ batch/async endpoints for backfills; avoid per-request overhead.
Chunk once, embed once.
Avoid re-embedding unchanged chunks; track doc hashes and only embed new/changed content.
Consider local for backfill.
sentence-transformers (e.g. all-MiniLM-L6-v2) are free; use for initial index, then optionally switch to hosted for queries if you need maximum quality.
Dimension vs cost.
Smaller dimensions (768–1024) are cheaper to store and query in the vector DB; compare total cost (embed + storage + query), not just embed price.
#
Conclusion
Embedding pricing varies 5–10x across providers. For volume, OpenAI small is hard to beat; for quality-per-dollar in RAG, Voyage and Cohere are worth testing. Optimize embedding cost where it moves the needle (big index, frequent re-embed), and don’t sacrifice retrieval quality for marginal savings.
For full RAG cost breakdown, see
RAG cost analysis
. For vector DB costs, see
Vector DB calculator
.
Estimate your embedding + LLM costs
Model your RAG pipeline: chunks, dimensions, and generation to see total cost.
Open Calculator
T
TokenBurner Team
AI Infrastructure Engineers
Engineers with hands-on experience building production AI systems. We've deployed RAG at scale and compared embedding costs across providers.
Learn more about TokenBurner →