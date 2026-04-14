---
source_url: https://encore.dev/blog/you-probably-dont-need-a-vector-database
fetched_at: 2026-04-14T06:00:00Z
category: technical
title: "You probably don't need a vector database — pgvector Guide"
---

# You probably don't need a vector database

*Encore Blog, March 9, 2026 — Ivan Cernja, 10 min read*

How vector embeddings, similarity search, and RAG pipelines work under the hood, and how pgvector handles all of it inside the PostgreSQL you already run.

Most backend teams adding AI features end up with a dedicated vector database running alongside their existing Postgres. A separate service for storing embeddings, a sync pipeline to keep documents and vectors consistent, another set of credentials and another deployment to monitor. For a documentation search over 30,000 entries or a support ticket classifier with 50,000 embeddings, that's a lot of infrastructure for what amounts to a nearest-neighbor query.

pgvector is a PostgreSQL extension that adds vector storage and similarity search directly to Postgres. Same distance metrics, same index types, same queries. Documents and their embeddings live in the same table, in the same transaction. For the workloads most teams actually have, it's enough.

## What a vector actually is

When you send text to an embedding model like OpenAI's text-embedding-3-small or Cohere's embed-v3, you get back a list of numbers. For OpenAI's model, it's 1,536 numbers. For their larger model, 3,072. Each number means nothing on its own. Together, they encode the semantic meaning of the input in a way that allows mathematical comparison.

The key property: texts with similar meanings produce vectors that are close together in this high-dimensional space. "Golden retriever puppy" and "young labrador dog" end up near each other. "Golden retriever puppy" and "quarterly earnings report" end up far apart.

This is why vector search works for things keyword search can't handle. A user searching for "how to handle errors in my API" should find a document titled "Exception handling and error responses in REST endpoints" even though the words barely overlap. Keyword search sees different strings. Vector search sees similar meanings.

## How similarity search works

Searching a vector database means finding the stored vectors closest to a query vector. "Closest" is defined by a distance metric. The three common ones:

- **Cosine similarity** measures the angle between two vectors, ignoring their magnitude. Two vectors pointing in roughly the same direction are similar regardless of their length. This is the default for most text embedding use cases.
- **L2 (Euclidean) distance** measures the straight-line distance between two points. Useful when the magnitude of the vector carries meaning, which it usually doesn't for text embeddings.
- **Inner product** is computationally cheaper and equivalent to cosine similarity when vectors are normalized, which most embedding models produce by default.

The naive approach to finding the nearest vectors is to compute the distance from the query to every stored vector and return the closest ones. This brute-force scan works fine for thousands of vectors, and it's exact.

At hundreds of thousands or millions of vectors, brute force gets slow. Index structures trade a small amount of accuracy for dramatically faster search. The two that pgvector supports:

- **IVF** partitions the vector space into clusters. At search time, only the clusters nearest to the query get scanned.
- **HNSW** builds a multi-layer graph where each vector is connected to its neighbors. Search starts at a random entry point and hops through edges toward the query, narrowing in through progressively denser layers.

Both index types return approximate results, meaning they might miss an edge-case nearest neighbor. In practice, recall rates above 95% are typical with default settings.

## What a RAG pipeline actually does

Retrieval-Augmented Generation (RAG) is the pattern behind most AI features that answer questions about your own data. Instead of fine-tuning a model on your documents, you retrieve relevant context at query time and include it in the prompt.

The pipeline has five steps:

1. **Embed the question.** The user's question gets sent to the same embedding model used to encode the documents.
2. **Search for similar vectors.** The query vector gets compared against stored document vectors. The top-k most similar documents come back, typically 3 to 10.
3. **Retrieve the documents.** The vector IDs map back to actual document content.
4. **Assemble the prompt.** The retrieved documents get injected into the LLM prompt as context.
5. **Generate the answer.** The LLM produces a response grounded in the retrieved documents.

The vector search step typically takes 5-50ms. The embedding API call takes 100-300ms. The LLM generation takes 500ms-3s. If you're optimizing for latency, the vector search is rarely the bottleneck.

This is worth keeping in mind when evaluating whether you need a dedicated vector database that searches in 2ms versus pgvector at 10ms. The difference is invisible to the user when the LLM generation takes a hundred times longer.

## pgvector does this inside Postgres

pgvector adds a vector column type and operators for similarity search. It supports cosine distance (<=>), L2 distance (<->), and inner product (<#>), with both HNSW and IVF indexing.

```sql
-- Enable the extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a table with a vector column
CREATE TABLE documents (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536)
);

-- Create an HNSW index for cosine similarity search
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

-- Find the 5 most similar documents to a query vector
SELECT id, title, 1 - (embedding <=> $1) AS similarity
FROM documents
ORDER BY embedding <=> $1
LIMIT 5;
```

The documents and their embeddings live in the same table. You can join vectors with application data in a single query. You can filter by metadata columns before running the similarity search. You can insert a document and its embedding in the same transaction, which means your search index is always consistent with your application state.

With a dedicated vector database, you store documents in Postgres and embeddings in a separate service. When you add a document, you write to both. When you delete one, you delete from both. If one write fails, you have either a document with no embedding or an orphaned vector. With pgvector, it's a single INSERT statement.

## One less service to manage

The infrastructure difference matters more than the performance difference. Adding a dedicated vector database means adding a service: another deployment, another set of credentials, another monitoring dashboard, another thing that can go down independently.

With a separate vector database, a semantic search feature touches three services: your application database for documents, the vector database for embeddings, and the embedding API for generating vectors. Each pair needs its own connection handling, retry logic, and failure mode.

With pgvector, the same feature touches two services: your database and the embedding API. The documents and vectors are in the same table. The consistency is transactional. The search is a SQL query.

pgvector handles millions of vectors with HNSW indexing. Benchmarks show query times under 20ms at 1M vectors with recall rates above 95%. That covers documentation search, support ticket classification, product recommendations, internal knowledge bases, and most other use cases teams actually build.

Where dedicated vector databases still win: billions of vectors, real-time index updates at massive write throughput, advanced multi-tenant filtered search with per-tenant isolation at scale, and managed auto-scaling with zero tuning. If you're building the next Perplexity or a search engine over the entire internet, pgvector isn't the answer. For everything else, it probably is.
