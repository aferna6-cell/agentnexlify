# Versioned eval results

One JSON per run, named `action-eval-<dataset_version>-<date>.json`. Each
records the git SHA, dataset version, engine (classifier / model / whether it
was LLM-backed), case count, every metric, the department confusion matrix, the
failed case ids, the safety-violation case ids, per-failure detail and the full
per-case outcome list.

Committed results are the project's record of how the system actually behaved on
a given commit. Re-running on the same day overwrites that day's file — commit
the one you intend to keep as the reference for a change.

Never compare an offline result to an LLM-backed one. `engine.llm_backed`
distinguishes them, and they are different systems.

The reference baseline is discussed in `docs/agent-action-eval.md`.
