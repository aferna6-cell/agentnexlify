# Routing ML experiment

Answers one question: **can a statistical classifier route small-business
requests better than the shipped heuristic, without giving up latency, cost,
interpretability or the ability to abstain?**

It is an experiment, not a deployment. Nothing here changes production routing.
The full write-up is `docs/ml-router-benchmark.md`.

## Layout

```
build_dataset.py   generates the training corpus (and drops eval collisions)
datasets.py        loads the three splits; leakage detection
heuristic.py       Model A - calls the real TypeScript classifier
train_tfidf.py     Model B - TF-IDF + logistic regression
train_embeddings.py Model C - frozen MiniLM embeddings + logistic regression
evaluate.py        shared metrics, risk/coverage, confidence analysis
compare.py         scores every model on one split with one metric implementation
export.py          writes router predictions for the TypeScript harness
data/              train-v1.jsonl
artifacts/         fitted models, reports, exported prediction tables
```

## Splits and what you may do with each

| Split | Source | Permission |
|---|---|---|
| train | `data/train-v1.jsonl` (1,216) | fit freely |
| validation | `agent-service/evals/datasets/validation/validation-v1.json` (30 labelled) | select models, inspect |
| **test (frozen)** | `agent-service/evals/datasets/action-eval-v1.json` (191 labelled) | **measure once, at the end** |

`datasets.py` is the only module that can reach the test split, and every
trainer takes its data from `load_train`. Run `python datasets.py` for the
leakage report; it must print `"clean": true`.

## Reproducing

```bash
pip install -r ../requirements.txt
python build_dataset.py          # deterministic: SEED=20260828
python datasets.py               # leakage check
python train_tfidf.py            # grouped CV + fit + validation report
python train_embeddings.py       # same, downloads MiniLM on first run
python compare.py --split validation
python compare.py --split test   # the final measurement

# End-to-end, from agent-service/
python export.py --model hybrid_tfidf --split test
cd ../../agent-service && npm run eval:actions -- --router ../ml/routing/artifacts/router-hybrid_tfidf-test.json
```

## Two things that would otherwise be invisible

**Cross-validation is grouped by template.** The corpus comes from ~200 authored
templates. Ordinary k-fold puts different slot-fills of one template in both the
fit and scoring folds, and then reports memorisation as generalisation: the first
run scored CV macro-F1 **0.998** against **0.70** on real validation data.
`StratifiedGroupKFold` on `template_id` closes that gap and the honest number is
**0.61**.

**Confidence is uncalibrated.** It is recorded and its quality is measured
(Brier, ECE, accuracy per bucket), because a router that abstains needs a
confidence that ranks. Nothing here adjusts it — that is Milestone 6.
