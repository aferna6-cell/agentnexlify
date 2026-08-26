---
title: pgvector 0.4.0 Performance — IVFFlat probes/lists Tuning on Supabase (2023, still-referenced baseline)
date: 2023-07-13
source_url: https://supabase.com/blog/pgvector-performance
fetched_at: 2026-08-26
category: technical
tags: [supabase, pgvector, ivfflat, probes, lists, benchmarks, ann, maintenance-work-mem, inner-product, historical]
---

# pgvector 0.4.0 Performance

*Supabase engineering blog. **July 13, 2023.** Predates HNSW (pgvector 0.5.0) — kept because it is the canonical IVFFlat tuning reference and the numbers are still cited. Treat absolute QPS as historical.*

## Benchmark setup

- ANN-Benchmarks methodology, `dbpedia-openai-1M` (1M vectors, 1,536 dims — OpenAI `text-embedding-ada-002` size).
- Supabase compute tiers from 2XL to 16XL.
- Metric: accuracy@10 vs queries per second.

## Results (IVFFlat)

| Setting | Accuracy@10 | QPS |
|---|---|---|
| `probes = 10` | 0.91 | 380 |
| `probes = 40` | 0.98 | 140 |
| 4XL, probes=10 | 0.91 | 270 |
| 8XL, probes=10 | 0.91 | 470 |
| 16XL, probes=10 | 0.91 | ~1,800 |

Accuracy and throughput trade off through `probes`; scaling compute scales QPS roughly linearly once the index is in RAM.

## Tuning guidance

- **`lists`**: use `vectors / 500`, not the older `/1000` rule of thumb. Higher `lists` → less of the index scanned per query (faster) but longer index build.
- Raise `maintenance_work_mem` for builds (article used 7,168 MB on large instances).
- **Prefer inner product** (`<#>`) for normalized embeddings — cheaper than cosine.
- **Pre-warm**: run 10–50k representative queries after build so the index pages are in cache before measuring.
- **Over-provision RAM** for the build and initial warm, then scale down.

## Roadmap noted at the time

pgvector 0.5.0: HNSW indexes, product quantization, parallel index builds — all since shipped.

## Notes for AgentNexLiFy

- Our KB embeddings (`knowledge-base/` pgvector + `scripts/reindex_contextual.py`) are far below 1M rows; IVFFlat vs HNSW choice matters less than keeping the index warm and using inner product on normalized vectors.
- If we switch to HNSW, the `lists`/`probes` knobs are replaced by `m` / `ef_construction` / `ef_search` — do not carry these numbers over.
- Compile note: pair with `raw/technical/tns-pgvector-benchmarks-lie.md` and `markaicode-supabase-pgvector-production-architecture-2026.md` for current-era guidance.
