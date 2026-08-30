# ML router benchmark

> **War room / decision status (2026-08-30):** This document is **historical research**
> from the Milestone 5–6 experiment track. The **authoritative production decision**
> for Milestone 6 is `docs/milestone-6-router-decision.md`, which explicitly **does
> not** promote TF-IDF or hybrid cascades to production yet despite routing-only
> gains on validation-v3. Do not treat the hybrid recommendation below as shipped
> policy.

**Question.** Can a statistical classifier route small-business requests better
than the shipped heuristic and LLM approaches, while preserving latency, cost,
interpretability and the ability to abstain?

**Answer.** Not as a replacement. As a *fallback* behind the heuristic, yes —
and the gain is real end to end, not just on a routing metric. The recommended
architecture is the hybrid, and it is recommended on evidence that includes one
finding pointing the other way.

Baseline commit `47d4923`. Experiment code: `ml/routing/`.

---

## 1. Why ML was introduced here

Milestone 4 repaired the decision pipeline: department accuracy 51.6% → 80.5%,
tool accuracy 3.6% → 66.7%, missed-action rate 92.9% → 29.8%, unsafe actions 0
throughout. What it did not fix was the shape of what remained. Routing became
**68.9% of all remaining failures**, and a large share of those were cases where
*no department accumulated any evidence at all* — every hand-written keyword and
every semantic rule missed.

That is a recall problem in a hand-maintained lexicon. Paraphrase is unbounded;
a keyword list is not. It is the one failure mode where a learned model has a
structural advantage over more rules, which is why this experiment happens now
and did not happen three milestones ago.

### A correction to the Milestone 4 figure

Milestone 4 reported "24 of 42 routing failures have zero heuristic evidence".
That conflated two different things. Measured directly:

| Condition | Frozen asks |
|---|---|
| Classifier returned **no candidate at all** | 4 |
| Classifier scored **below the orchestrator's routing floor** (`MIN_BUSINESS_EVIDENCE = 3`) | 32 |
| Of those, cases with a department label (i.e. scoreable) | 19 |

"Got none" in the Milestone 4 taxonomy meant *the orchestrator did not route*,
which includes deterministic declines (non-business, destructive, system-meta)
as well as classifier silence. The addressable surface for a fallback model is
the **19 below-floor department-labelled cases**, not 24. The earlier number
overstated it.

---

## 2. Dataset construction

### Training split — `ml/routing/data/train-v1.jsonl`

**1,216 examples, 8 departments, 36 intent families, ~200 authored templates.**

| Department | n | | Style | n |
|---|---|---|---|---|
| invoicing | 165 | | terse | 292 |
| marketing | 164 | | plain | 291 |
| operations | 160 | | conversational | 167 |
| sales | 156 | | long_context | 164 |
| people | 153 | | typo | 160 |
| accounting | 147 | | shouty (all caps) | 142 |
| customer_service | 141 | | | |
| admin_records | 130 | | | |

Each example carries **only what a production router sees**: the ask, and its
department label. No rationale, no expected tool, no expected behaviour. A
router that learns from downstream labels is not solving routing.

Written independently of the benchmark. Deliberate properties:

- **Intent families, not department blobs.** What separates People from
  Marketing is not the department, it is "hiring ad" vs "weekend sale".
  Families make those boundaries explicit and let the corpus be balanced per
  department rather than per template.
- **18 authored boundary-contrast pairs**, each generated four ways —
  `post a hiring ad` (People) vs `post our weekend sale` (Marketing);
  `payroll taxes` (Accounting) vs `add our new employee to payroll` (People);
  `note on X's record that she approved the quote` (Admin) vs
  `put together a quote for X` (Sales).
- **Six surface styles**, applied round-robin — terse lowercase, conversational
  prefixes, injected typos (`apointment`, `invocie`, `teh`), all-caps, and
  long trailing context clauses.
- **Six verticals** (auto, salon, plumbing, dental, landscaping, HVAC),
  deliberately over-represented relative to the benchmark's single auto shop.
  A router that has only seen brake jobs has memorised a vocabulary.
- **`none` is not a class.** Out-of-scope, destructive and system-meta asks are
  refused deterministically by the orchestrator before any classifier runs. A
  model that could predict "none" would be a model with an opinion about policy.

### Leakage control

Two independent checks in `datasets.py`, run as a script:

1. exact match on normalised text;
2. near-duplicate match on token Jaccard ≥ 0.8.

The check found a real collision on its first run — an independently authored
`"what phone number do we have on file for the business"` against the frozen
`"what phone number do we have on file for the shop?"` (similarity 0.833). The
template was rewritten, **and** `build_dataset.py` now drops any generated row
that collides, so the class of problem is closed rather than the instance.

Current state: `train_vs_validation_overlaps: 0`, `train_vs_test_overlaps: 0`,
`clean: true`.

---

## 3. The cross-validation trap

The first TF-IDF run reported **CV macro-F1 0.998** and scored **0.70** on the
real validation split. The model had not generalised; ordinary k-fold had put
different slot-fills of the *same template* in both the fit and the scoring
fold, so it was scoring memorisation.

Fixed with `StratifiedGroupKFold` grouped on `template_id` (200 groups), which
guarantees a template never appears on both sides of a fold:

| Configuration | Random 5-fold | **Grouped 5-fold** |
|---|---|---|
| word(1,2)+char(3,5) C=4 | 0.998 | **0.607** |

The grouped number is the honest one and is what model selection used. Any
generated-data experiment that reports near-perfect CV should be assumed to
have this bug until it proves otherwise.

---

## 4. Models

| | Model | Description |
|---|---|---|
| **A** | Heuristic (production) | The shipped `classifyHeuristic`, called through a Node bridge rather than reimplemented, so the baseline is the real thing |
| **B** | TF-IDF + LR | word(1,2) + char_wb(3,5), sublinear TF, C=4, multinomial logistic regression |
| **C** | Embedding + LR | frozen `all-MiniLM-L6-v2` (384-d, CPU, local), logistic regression head, C=10 |
| **D** | LLM (Haiku) | The shipped `classifyWithHaiku` path — **not measured**, see §8 |
| **E** | Hybrid | Heuristic, with B or C answering only where the heuristic falls below the production evidence floor |

Hyperparameters were chosen by grouped CV over a deliberately small grid (6
configs for B, 4 for C). The point of this milestone is whether a classical
model is *competitive*, not to squeeze a final half-point out of one.

The hybrid's trigger is `MIN_BUSINESS_EVIDENCE = 3`, **taken from production
code** (`_orchestrator.ts`), not tuned against any split. It is the exact
boundary at which the shipped system already declines to route.

---

## 5. Validation results (30 labelled cases)

| Router | Accuracy | Macro F1 | Top-2 | p50 ms | p95 ms |
|---|---|---|---|---|---|
| **Heuristic (prod)** | **80.0%** | **0.7901** | 80.0% | 0.20 | 2.22 |
| TF-IDF + LR | 73.3% | 0.7028 | 76.7% | 1.62 | 1.91 |
| Embedding + LR | 63.3% | 0.6787 | 73.3% | 12.87 | 16.10 |
| Hybrid (either) | 80.0% | 0.7901 | 80.0% | 0.20 | 2.22 |

Two things this split cannot tell us, both worth stating plainly:

1. **The heuristic beats both ML models outright.** Milestone 4 improved the
   baseline substantially, so the ML models are competing against a much
   stronger opponent than the one that motivated the experiment.
2. **The validation split no longer contains the failure mode.** Milestone 4
   took validation routing to 97%, so there are *zero* below-floor cases left in
   it — which is why the hybrids are numerically identical to the heuristic
   here. Model selection between B and C for the fallback role therefore could
   not be settled on validation, and grouped CV disagreed with it (embeddings
   0.673 > TF-IDF 0.607 on CV; TF-IDF 0.703 > embeddings 0.679 on validation).
   **Both hybrids were carried into the frozen evaluation as finalists**, which
   is the honest response to a split that cannot discriminate.

With 30 cases and 6 departments present, several per-department F1 scores rest
on n=1. They are reported for completeness and should not be read as signal.

---

## 6. Frozen test results — routing only (191 labelled cases)

Run once, after the experiment was frozen.

| Router | Accuracy | Macro F1 | Top-2 | p50 ms | p95 ms | Cost/1k | Size |
|---|---|---|---|---|---|---|---|
| Heuristic (prod) | 75.4% | 0.6786 | 82.7% | **0.08** | **0.28** | $0 | 0 (rules) |
| TF-IDF + LR | 72.8% | 0.6614 | **85.9%** | 1.58 | 1.96 | $0 | 861 KB |
| Embedding + LR | 63.3% | 0.5775 | 76.4% | 11.49 | 16.67 | $0 | 90 MB + 13 KB |
| **Hybrid: heur → TF-IDF** | **77.0%** | 0.6773 | **85.9%** | 0.09 | 1.69 | $0 | 861 KB |
| Hybrid: heur → Embed | 76.4% | **0.7141** | 85.3% | 0.09 | 11.56 | $0 | 90 MB + 13 KB |
| LLM (Haiku) | *not measured* | — | — | — | — | ~$1.10 | n/a |

> The 75.4% here and the 80.5% in Milestone 4 are **different denominators**.
> This table scores the 191 department-labelled cases; Milestone 4's figure
> covers all 215 including the 24 `none` cases, most of which the system gets
> right by declining. They are not comparable and neither is wrong.

### Per-department F1

| Department | n | Heuristic | TF-IDF | Embed | Hyb→TFIDF | Hyb→Embed |
|---|---|---|---|---|---|---|
| accounting | 4 | 0.308 | 0.167 | 0.333 | 0.222 | **0.667** |
| admin_records | 48 | 0.894 | **0.898** | 0.720 | 0.887 | 0.860 |
| customer_service | 16 | 0.600 | 0.625 | 0.571 | 0.667 | **0.720** |
| invoicing | 25 | **0.816** | 0.640 | 0.702 | 0.784 | 0.784 |
| marketing | 21 | 0.718 | **0.773** | 0.636 | 0.732 | 0.718 |
| operations | 13 | 0.526 | **0.741** | 0.571 | 0.526 | 0.500 |
| people | 7 | 0.800 | 0.769 | 0.500 | **0.824** | 0.706 |
| sales | 57 | 0.767 | 0.679 | 0.586 | **0.777** | 0.758 |

This is the table that stops "TF-IDF is worse" from being the conclusion.
Standalone TF-IDF loses on average while **winning decisively on Operations**
(0.741 vs 0.526) — it recovers the `operations → sales` confusions the keyword
surface cannot. It loses badly on Invoicing (0.640 vs 0.816). The two models
fail in different places, which is exactly the condition under which combining
them beats either.

### Zero-evidence recovery

Of the **19** department-labelled frozen cases below the production evidence
floor (heuristic correct on 3 of them):

| Model | Recovered | Rate |
|---|---|---|
| TF-IDF + LR | 6 / 19 | 32% |
| Embedding + LR | 5 / 19 | 26% |

Modest in isolation, and it is where the hybrid's whole gain comes from. Their
expected departments: sales 9, admin_records 4, customer_service 3, marketing 1,
people 1, accounting 1.

---

## 7. Frozen test results — end to end

Routing accuracy is not the product. Each candidate was replayed through the
**full 215-case action benchmark** behind the router substitution seam, so the
downstream consequences are visible.

| Router | Dept | Behavior | Tool | Params | Missed-action | **Unsafe** |
|---|---|---|---|---|---|---|
| Baseline (shipped) | 80.5% | 80.0% | 66.7% | 70.1% | 29.8% | **0 / 59** |
| TF-IDF standalone | 81.9% | **88.4%** | 67.9% | 68.8% | **25.0%** | **0 / 59** |
| Embedding standalone | 75.8% | 83.7% | 56.0% | 57.1% | 35.7% | **0 / 59** |
| **Hybrid: heur → TF-IDF** | **85.1%** | 85.6% | **67.9%** | **70.1%** | 26.2% | **0 / 59** |
| Hybrid: heur → Embed | 83.7% | 85.1% | 66.7% | 70.1% | 26.2% | **0 / 59** |

**Hybrid → TF-IDF versus the shipped baseline:** department +4.6 pp, behavior
+5.6 pp, tool +1.2 pp, missed-action −3.6 pp, parameters unchanged, p95 latency
1.589 ms vs 1.556 ms. **Unsafe actions remain 0.**

The embedding standalone router is the case that justifies running this at all:
it *looks* only moderately worse on routing (75.8% vs 80.5%) and is
**catastrophic downstream** — tool accuracy 56.0%, parameters 57.1%,
missed-action up to 35.7%. Judged on routing alone it would have been a
defensible second choice. It damages the product.

---

## 8. Model D — the LLM router was not measured

No `ANTHROPIC_API_KEY` exists in this environment, so the shipped
`classifyWithHaiku` path could not be run. This is stated rather than papered
over, and the harness to run it exists and is committed
(`agent-service/evals/export-llm-predictions.ts`,
`npm run eval:export-llm`).

What the harness does when a key is present:

- calls `classifyWithHaiku` **directly**, not `classify`, so a malformed or
  unmappable response records as `null` instead of being silently absorbed by
  the heuristic fallback — the benchmark must not credit the LLM with the
  heuristic's answers;
- reports `fallback_would_be_used` per case, giving the malformed/fallback rate
  the milestone asks for as a separate number.

What can be stated without running it — computed from the real prompt
(registry catalogue + fixed instructions + the ask) at Haiku pricing:

| | |
|---|---|
| Input tokens per call | ~642 (≈4 chars/token) |
| Output tokens per call | ~90 |
| **Cost per 1,000 routes** | **~$1.10** |
| Cost for one 215-case benchmark run | ~$0.24 |

Prompt caching is not modelled; with the catalogue cached the input cost would
fall materially. Even so: the hybrid costs **$0** per 1,000 routes and adds
~1.6 ms at p95, against a network round trip and ~$1.10. The LLM would have to
be *substantially* more accurate to justify that in a hot path, and this
experiment cannot say whether it is.

**Limitation, stated plainly:** every number in this document measures the
offline heuristic path. Production routes with Haiku when a key is present. The
single most valuable follow-up is to run this harness with credentials.

---

## 9. Confidence — measured, not calibrated

| Router | Brier | ECE | mean conf when right | when wrong |
|---|---|---|---|---|
| Heuristic (prod) | 0.146 | 0.044 | 0.835 | 0.658 |
| TF-IDF + LR | 0.155 | **0.111** | 0.691 | 0.417 |
| Embedding + LR | 0.183 | 0.046 | 0.760 | 0.540 |
| Hybrid → TF-IDF | 0.147 | **0.032** | 0.826 | 0.677 |

**All values are uncalibrated.** Nothing here adjusts them; that is Milestone 6.

The headline number is misleading on its own, and the bucket table is the
finding:

| Confidence bucket | Heuristic n / acc | TF-IDF n / acc |
|---|---|---|
| 0.2–0.4 | 1 / 0% | 46 / 33% |
| 0.4–0.6 | 21 / 33% | 48 / 71% |
| 0.6–0.8 | 12 / 75% | 42 / 86% |
| 0.8–1.0 | **154 / 83%** | 55 / **98%** |

The heuristic has the better ECE and the **worse** confidence. It puts 154 of
191 cases in one top bucket at 83% accuracy — the number barely separates
anything, because `score/(score+2)` saturates. TF-IDF spreads across all four
buckets with monotone accuracy 33% → 71% → 86% → 98%. For **selective
classification, which needs ranking rather than absolute correctness**, the
TF-IDF signal is far more useful, and a low ECE on a signal that never varies is
not a virtue.

---

## 10. Risk / coverage

Accuracy on the subset each router is permitted to decide, at the nearest
achievable coverage. No production threshold was changed.

| Target coverage | Heuristic | TF-IDF | Embedding | Hybrid → TF-IDF |
|---|---|---|---|---|
| 100% | 76.6% @98% | 72.8% | 63.3% | **77.0%** |
| 95% | 77.0% @98% | 74.2% @97% | 65.6% @94% | **79.7% @95%** |
| 90% | 82.0% | 76.4% @91% | 68.5% @86% | **82.1% @91%** |
| 80% | 83.1% @81% | **85.5% @76%** | 72.0% @79% | 83.1% @81% |
| 70% | 83.1% @81% | **85.6% @69%** | 75.4% @72% | 83.1% @81% |
| 60% | **93.3% @47%** | 90.8% @62% | 77.9% @64% | 93.3% @47% |

The heuristic's curve is nearly flat between 100% and 80% coverage and then
jumps — a direct consequence of the confidence compression above; there is no
useful operating point in between because 80% of the mass shares one confidence.
TF-IDF's curve descends smoothly, so abstention actually buys accuracy at every
step. That is the property a production abstention policy needs, and it is an
argument for the ML confidence signal independent of which model routes.

---

## 11. Error analysis

**Where the hybrid gains:** entirely on the 19 below-floor cases, 6 of which
TF-IDF recovers. No other case changes, by construction.

**What each model is good and bad at:**

- *Heuristic* — strong where the vocabulary is explicit (admin_records 0.894,
  invoicing 0.816). Weak on Operations (0.526), which it loses to Sales, and on
  Accounting (0.308, n=4).
- *TF-IDF* — recovers Operations (0.741) and Marketing (0.773). Loses Invoicing
  badly (0.640): it routes invoicing language to Sales seven times, because
  outbound-customer vocabulary dominates both in the training corpus.
- *Embeddings* — worst overall, and specifically weak on the long tail
  (people 0.500, admin_records 0.720). MiniLM's 384-d sentence vectors appear to
  wash out exactly the short imperative distinctions this task turns on:
  `note on X's record` and `email X about the quote` are semantically close and
  operationally opposite.
- *Multi-intent and long-context asks* remain the shared failure. Both models
  see one bag of the whole sentence; neither has a mechanism for "the task verb
  governs this noun and not that one" — which is exactly the distinction
  Milestone 4 had to build by hand in `_intent.ts`.

**Departments with n < 8 on the frozen split** (accounting n=4, people n=7)
produce F1 swings of ±0.3 from a single case. Differences there are noise.

---

## 12. Recommendation

**Adopt the hybrid — heuristic first, TF-IDF where the heuristic falls below the
production evidence floor — as the offline router. Do not replace the heuristic,
and do not deploy the embedding model.**

Evidence:

| Criterion | Verdict |
|---|---|
| End-to-end department accuracy | 80.5% → **85.1%** |
| End-to-end behavior accuracy | 80.0% → **85.6%** |
| Missed-action rate | 29.8% → **26.2%** |
| Tool / parameter accuracy | up or unchanged |
| **Unsafe actions** | **0, unchanged** |
| Added p95 latency | **+0.03 ms** (fallback fires on ~17% of asks) |
| Cost | **$0** — local inference, no network |
| Artifact size | 861 KB |
| Interpretability | Feature weights inspectable; the heuristic still answers 83% of asks |
| Failure mode if the model is wrong | Bounded: it only ever answers where the shipped system currently answers *nothing* |

That last row is why this is the recommendation rather than "TF-IDF standalone
had the best behavior accuracy". The hybrid cannot regress a case the heuristic
handles, because it never sees one. Standalone TF-IDF changes every routing
decision in the product on the strength of a 30-case validation split and a
synthetic training corpus, and its per-department table shows it would cost
Invoicing recall to buy Operations recall.

This is conclusion **D** (hybrid) from the milestone's list, arrived at because
the models fail in different places, not because a hybrid sounded safest.

### Deployment shape

**Option C — precomputed classifier consumed by the JS engine — is not viable**
for production (it only works for a fixed ask set, which is why the benchmark
uses it). Of the remaining options, **Option A: export the fitted model and run
inference in-process** is the recommendation. TF-IDF + logistic regression is a
vocabulary, an IDF vector and a weight matrix; it is portable to TypeScript
without a Python runtime, a service hop, or a new failure domain in the hot
path. The seam already exists: `setRoutingProvider` in `_classifier.ts`.

**Do not build that yet.** The evidence supporting this recommendation has two
soft spots — a 30-case validation split and an unmeasured LLM path — and both
are cheaper to close than the integration is to build.

---

## 13. Limitations

1. **The LLM router was never measured.** No credential. Everything here
   compares against the offline path; production uses Haiku when keyed.
2. **The validation split is 30 cases** and contains none of the failure mode
   under study. Model selection between B and C could not be settled on it.
3. **Training data is synthetic**, from ~200 authored templates. Grouped CV
   controls the optimistic bias but does not remove the distribution gap
   between authored and real owner language.
4. **Frozen-split department counts are small** for accounting (4) and people
   (7); per-department differences there are noise.
5. **No calibration, by design.** Confidence values rank; they are not
   probabilities.
6. `compare.py --split test` was executed twice to display different sections of
   the same deterministic output. No model, feature or hyperparameter changed
   between those runs, and nothing was refitted after any frozen measurement.

---

## 14. Reproducibility

| | |
|---|---|
| Git SHA | recorded in every artifact under `ml/routing/artifacts/` |
| Seed | `20260828` (dataset generation, CV shuffling, both classifiers) |
| Train version | `routing-train-v1` (1,216 rows) |
| Validation version | `action-eval-validation-v1` |
| Test version | `action-eval-v1` |
| Python | 3.12.3 |
| Packages | `ml/requirements.txt` (numpy 2.5.2, pandas 3.0.5, scikit-learn 1.9.0, sentence-transformers 6.0.0, torch 2.13.0) |
| CV scheme | `StratifiedGroupKFold(5)` grouped by `template_id`, 200 groups |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2`, frozen, CPU |

`build_dataset.py` uses a SHA-1 template hash rather than Python's `hash()`,
which is salted per process and would silently change the CV folds between runs
of a script whose purpose is reproducibility.

---

## 15. Safety boundary

The router chooses a department. It has no authority over approval
requirements, risk levels, tool execution, tenant scope, action policy,
verification, or destructive-action refusal — all of which remain deterministic
and are enforced by the action executor, which never consults the classifier.

`setRoutingProvider` can change routing and nothing else. No model was trained
to decide whether it may bypass policy, and `none` was deliberately excluded
from the label space so a classifier cannot express an opinion about
out-of-scope or destructive requests.

Unsafe actions: **0 / 59 in every configuration measured**, including the two
routers that damaged downstream accuracy.

---

## 16. Recommended Milestone 6

**Close the two soft spots before building anything.**

1. **Measure the LLM router.** The harness is committed and costs ~$0.24 for a
   full frozen run. Until it runs, "the ML router beats the LLM" is unsupported —
   the comparison has never been made.
2. **Grow the validation split** to a few hundred labelled asks, ideally from
   real owner traffic. Every model-selection decision here rests on 30 cases.
3. **Then calibrate** (temperature scaling or isotonic on validation) and set an
   abstention threshold from the risk-coverage curve. The confidence analysis
   above is the input to that work: the heuristic's signal is compressed and the
   TF-IDF signal is not, which suggests the abstention policy should read the ML
   confidence even if the heuristic keeps routing.

**Largest remaining failure category:** routing, still — but its shape has
changed again. It is no longer lexicon recall; the hybrid addresses that. What
remains is *department-boundary confusion on multi-intent and long-context
asks*, where a single bag-of-features representation cannot express which noun
the task verb governs.
