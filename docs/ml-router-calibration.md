# Milestone 6 — Router calibration, LLM benchmark, and selective routing

**Status:** complete. **Production routing is unchanged.**
**Commit:** `1c2c9e7` (baseline) → this branch. **Date:** 2026-08-29.

The question this milestone set out to answer, for each incoming request:

> Should AgentNexLiFy trust the heuristic, fall back to TF-IDF, escalate to the
> LLM, or abstain and ask the owner?

The answer is below, and part of it is *"we still cannot say"* — for a specific,
named reason that is itself the main recommendation for Milestone 7.

---

## 1. Problem

Milestone 5 ended with a recommendation (heuristic → TF-IDF) and two admitted
holes:

1. **Model D — the live Haiku router that production actually uses when keyed —
   had never been measured.** Every routing number in Milestone 5 described the
   offline heuristic path.
2. **The 35-case validation split was answering ~97% correctly.** A split the
   system already passes cannot separate candidate architectures: every
   candidate scores the same on it, so it has stopped being evidence.

Hole 2 made hole 1 worse. Without a split that discriminates, there was no way
to tell whether a router that beat the heuristic was better or merely different.

## 2. Why calibration is needed

Three routers, three numbers that look alike and mean nothing alike:

| Source | "Confidence" is | Range behaviour |
|---|---|---|
| Heuristic | `score / (score + 2)` | Saturates. A one-point evidence lead is 0.17 between weak candidates and 0.02 between strong ones. |
| TF-IDF + LR | Max class probability | A real probability, but of the *label*, not of *being right*. |
| Haiku | A number the model wrote about itself | Unknown. Not measured (§5). |

A cascade rule of the form `if tfidf_conf > heuristic_conf: use tfidf` is
therefore not a comparison. It is a coincidence of arithmetic between two
unrelated scales, and it would silently encode whichever scale happened to run
hotter. Calibration is what makes such a rule legitimate: afterwards every
source's number answers the same question — *"of the predictions I make at this
confidence, what fraction are correct?"* — and only then can two of them share
an axis.

This is also why `RouterDecision` (§13 below) keeps `raw_score` and
`calibrated_confidence` in **separate fields** and never lets one default to the
other.

## 3. Validation expansion

`agent-service/evals/datasets/validation/validation-v2.json` — authored by
`ml/routing/authoring/build_validation_v2.py`, which is committed so every case
is traceable to the argument that labelled it.

| | v1 | v2 |
|---|---|---|
| Cases | 35 | **200** |
| Routable (department-labelled) | 30 | **184** |
| Policy-decided (`none`) | 5 | 16 |
| Departments with ≥20 cases | 1 | **8** |

Per-department: accounting 23, admin_records 24, customer_service 20,
invoicing 24, marketing 23, operations 24, people 23, sales 23.

Every case carries a `stress` label naming the routing boundary it probes, so
accuracy can be reported by difficulty instead of pooled into one number that
hides where the failures concentrate:

| Stress axis | n | | Stress axis | n |
|---|---|---|---|---|
| high_evidence | 34 | | typo | 14 |
| novel_phrasing | 28 | | zero_evidence | 14 |
| misleading_noun | 17 | | hard_negative | 13 |
| long_context | 15 | | subject_intent_mismatch | 10 |
| department_boundary | 15 | | ambiguous | 9 |
| short_command | 14 | | multi_intent | 9 |
| | | | low_evidence | 5 |

The split is materially harder than v1, which was the point. The heuristic scores
**47.3%** here against **75.4%** on the frozen split — v2 concentrates on exactly
the boundaries the frozen set samples only incidentally.

**No frozen failure was cloned.** Cases were written from the fixture business
(Sunset Auto Care) against the department semantics in `departments.ts`, and the
labels argue from the request, not from what the system happened to output.

## 4. Leakage controls

`ml/routing/leakage.py`. Milestone 5 had two detectors; both are retained, and
three are added. The additions exist because exact-match and Jaccard are both
**bag-of-words** tests, and a bag of words cannot see word order or morphology.

| Detector | Catches |
|---|---|
| EXACT | Identical after lowercasing and stripping punctuation. |
| NORMALISED | Adds unicode quote/dash unification, whitespace collapse. `"email sarah."` vs `"Email Sarah"`. |
| JACCARD ≥ 0.80 | Token overlap. Reorderings and small edits. |
| NGRAM (char-4 cosine ≥ 0.85) | Order-aware and morphology-tolerant. `"invoicing wallace"` vs `"invoice wallace"`. This is the one that catches a *reworded* template. |
| TEMPLATE_FAMILY | Widens any hit from the row to the whole generator template — if a template can emit one collision it can emit others, so the exposure is the family. |

**Result: 0 collisions**, all three split pairs, all five detectors.

```
train 1216 · validation-v2 184 · test 191
train_vs_validation:  0        train_vs_test: 0        validation_vs_test: 0
```

Nothing is dropped silently. `build_dataset.py` owns the decision to drop a
colliding *training* row and prints the count when it does; `leakage.py` only
reports. A leakage report whose headline is "0" because the evidence was deleted
before counting is worse than no report.

## 5. LLM benchmark (Model D) — NOT MEASURED

**There is no `ANTHROPIC_API_KEY` in this environment. Model D remains
unmeasured, and no number in this report describes it.**

What exists:

- The harness is committed and runnable: `evals/export-llm-predictions.ts`,
  driven by `ml/routing/milestone6.py`. It calls **`classifyWithHaiku` directly,
  never `classify()`** — `classify()` falls back to the heuristic on failure,
  and scoring that blend would credit the LLM with the heuristic's answers.
- Malformed/unmappable output is counted as its own rate rather than absorbed
  into the fallback.
- Measured cost of running it: **$1.10 per 1,000 routes**
  (`claude-haiku-4-5-20251001`, ~651 input + 90 output tokens per call;
  $0.20 for a full 184-case validation pass). Prompt caching is not modelled;
  with the catalogue cached, input cost would be materially lower.

What is measurable without a credential, and *is* measured: the **escalation
rate** — the share of traffic that would reach the LLM — because it is fixed by
the deterministic stages ahead of it. That is the cost driver.

| Architecture | LLM calls / 1k (validation) | $ / 1k | (frozen) |
|---|---|---|---|
| D: LLM only | 1000 | $1.101 | 1000 |
| E: heuristic → LLM | 435 | $0.479 | 100 |
| F: heuristic → TF-IDF → LLM | 234 | $0.257 | 47 |

Routing accuracy through the LLM is **not** reported, estimated, or substituted.

## 6. Reliability diagrams

Cross-fitted, 5-fold, out-of-fold. Every calibrated value below was produced by a
calibrator that had not seen its own case.

**Heuristic, raw (chosen: identity):**

| Bin | n | Mean conf | Accuracy | Gap |
|---|---|---|---|---|
| 0.0–0.1 | 41 | 0.000 | 0.000 | +0.000 |
| 0.3–0.4 | 6 | 0.333 | 0.167 | −0.166 |
| 0.5–0.6 | 42 | 0.521 | 0.357 | **−0.164** |
| 0.6–0.7 | 9 | 0.667 | 0.333 | **−0.334** |
| 0.7–0.8 | 21 | 0.730 | 0.809 | +0.079 |
| 0.8–0.9 | 46 | 0.835 | 0.783 | −0.053 |
| 0.9–1.0 | 19 | 0.913 | 0.789 | −0.124 |

The heuristic is **overconfident in the middle of its range**. The 0.5–0.7 band
claims 52–67% and delivers 33–36%.

**TF-IDF, temperature-calibrated (T = 0.2, identical across all 5 folds):**

| Bin | n | Mean conf | Accuracy | Gap |
|---|---|---|---|---|
| 0.1–0.2 | 10 | 0.189 | 0.100 | −0.089 |
| 0.2–0.3 | 39 | 0.243 | 0.282 | +0.039 |
| 0.3–0.4 | 21 | 0.344 | 0.333 | −0.011 |
| 0.4–0.5 | 19 | 0.455 | 0.421 | −0.034 |
| 0.5–0.6 | 16 | 0.545 | 0.562 | +0.017 |
| 0.6–0.7 | 21 | 0.659 | 0.714 | +0.055 |
| 0.7–0.8 | 16 | 0.757 | 0.812 | +0.055 |
| 0.8–0.9 | 31 | 0.856 | 0.839 | −0.018 |
| 0.9–1.0 | 11 | 0.928 | 1.000 | +0.072 |

After calibration TF-IDF's stated confidence tracks its accuracy to within ~0.09
everywhere and under 0.06 across most of the range. This number can carry a
threshold.

## 7. ECE / Brier results and calibrator selection

| Router | Method | ECE raw | ECE out-of-fold | ECE in-fold | Overfit gap | Brier out | Verdict |
|---|---|---|---|---|---|---|---|
| Heuristic | identity | 0.0942 | 0.0942 | 0.0942 | 0.0000 | 0.1568 | **chosen** |
| | platt | 0.0942 | 0.0846 | 0.0844 | +0.0001 | 0.1549 | gain 0.010 < 0.02 bar |
| | isotonic | 0.0942 | 0.0861 | **0.0000** | **+0.0861** | 0.1525 | **rejected — overfit** |
| | temperature | 0.0942 | 0.1148 | 0.1228 | −0.0081 | 0.1789 | worse than raw |
| TF-IDF | identity | 0.0718 | 0.0718 | 0.0778 | −0.0060 | 0.1850 | baseline |
| | platt | 0.0718 | 0.1129 | 0.1013 | +0.0117 | 0.1933 | worse than raw |
| | isotonic | 0.0718 | 0.1011 | **0.0000** | **+0.1011** | 0.1922 | **rejected — overfit** |
| | temperature | 0.0718 | **0.0377** | 0.0445 | −0.0068 | 0.1812 | **chosen** |

**Isotonic regression was rejected for both routers**, and the mechanism is
visible in the table: in-fold ECE of exactly 0.0000 against out-of-fold 0.086 /
0.101. It memorised its own fold. On 184 points that is the expected outcome for
a non-parametric fit, and the selection rule caught it rather than the reader
having to.

Selection rule (`calibration.select_calibrator`), applied in order
identity → platt → temperature → isotonic:

- must improve out-of-fold ECE by **> 0.02** to displace the incumbent, and
- must show an overfit gap **≤ 0.05**.

So a more expressive calibrator has to earn its place twice: once on accuracy of
meaning, once on transfer.

**Two honest caveats.**

1. The heuristic keeps its **raw** confidence. That is the correct call under
   the rule, but ECE is traffic-weighted, and the heuristic's worst bin
   (0.6–0.7, gap −0.334) holds only 9 cases and therefore barely moves it. The
   heuristic's confidence should not be treated as a probability anywhere, and
   nothing in this milestone does.
2. Temperature `T = 0.2` was identical across all five folds — stable, not a
   fold artefact. `T < 1` *sharpens*, meaning the raw LR probabilities were
   under-confident relative to their accuracy.

## 8. Risk / coverage

Accuracy among the requests the router was allowed to decide, validation-v2:

| Coverage | A: heuristic | B: TF-IDF | C: heur→TF-IDF | C2: heur→embed | G: heur→TF-IDF→ask |
|---|---|---|---|---|---|
| 100% | 60.8% | 54.9% | 57.1% | 63.0% | 73.1% |
| 95% | 60.8% | 57.1% | 60.0% | 65.7% | 73.1% |
| 90% | 60.8% | 59.6% | 63.2% | 66.3% | 73.1% |
| 85% | 60.8% | 62.2% | 65.4% | 68.0% | 73.1% |
| 80% | 60.8% | 63.9% | 68.0% | 68.0% | 73.1% |
| 70% | 66.7% | 66.7% | 72.9% | 71.3% | 72.9% |

The **abstention sweep** is the direct answer to the milestone's central
question. Architecture G, heuristic → TF-IDF → ask the owner, at varying
calibrated-confidence thresholds:

| Abstain below | Coverage | Owner clarifications | Accuracy on routed | **Risk on routed** | End-to-end |
|---|---|---|---|---|---|
| 0.00 | 100.0% | 0.0% | 57.1% | 42.9% | 57.1% |
| 0.30 | 83.2% | 16.9% | 66.7% | 33.3% | 55.4% |
| 0.40 | 76.6% | 23.4% | 70.2% | 29.8% | 53.8% |
| 0.50 | 72.3% | 27.7% | 71.4% | 28.6% | 51.6% |
| **0.55** | **70.7%** | **29.3%** | **73.1%** | **26.9%** | 51.6% |
| 0.70 | 65.2% | 34.8% | 74.2% | 25.8% | 48.4% |
| 0.90 | 57.1% | 42.9% | 73.3% | 26.7% | 41.9% |

Abstention works: it cuts risk among auto-routed requests from **42.9% → 26.9%**.
It also costs 29.3% owner interruptions, and returns diminish sharply past 0.7.
A router that reached 98% by asking about half of all requests would look
excellent in the "accuracy on routed" column and be a bad product; that column is
never quoted here without the clarification rate beside it.

## 9. Cascade comparison and utilisation

Validation-v2, 184 routable cases:

| Architecture | End-to-end acc | Coverage | Owner clarification | LLM/1k | p95 latency |
|---|---|---|---|---|---|
| A: heuristic only | 47.3% | 77.7% | 22.3% | 0 | 0.33 ms |
| B: TF-IDF only | 54.9% | 100.0% | 0.0% | 0 | 1.90 ms |
| C: heuristic → TF-IDF | 57.1% | 100.0% | 0.0% | 0 | 1.98 ms |
| C2: heuristic → embedding | **63.0%** | 100.0% | 0.0% | 0 | 13.24 ms |
| D: LLM only | — | — | — | 1000 | — |
| E: heuristic → LLM | — | — | — | 435 | — |
| F: heuristic → TF-IDF → LLM | — | — | — | 234 | — |
| G: heuristic → TF-IDF → ask | 51.6% | 70.7% | 29.3% | 0 | 1.98 ms |

Stage utilisation for C on validation: heuristic decides **56.5%**, TF-IDF
**43.5%**, owner **0%**. On frozen: heuristic **90.0%**, TF-IDF **10.0%**.
The fallback carries four times as much traffic on v2 as on the frozen set —
another way of saying v2 is the harder split.

**Pareto front (validation).** Nothing is dominated. Every measured architecture
sits on the front, trading routing error against owner interruption against
latency:

| Architecture | Routing errors/1k | Clarifications/1k | $/1k | p95 |
|---|---|---|---|---|
| G: heur → TF-IDF → ask | **190.2** | 293.5 | $0 | 1.98 ms |
| A: heuristic only | 304.3 | 222.8 | $0 | **0.33 ms** |
| C2: heur → embedding | 369.6 | **0.0** | $0 | 13.24 ms |
| C: heur → TF-IDF | 429.3 | **0.0** | $0 | 1.98 ms |
| B: TF-IDF only | 451.1 | **0.0** | $0 | 1.90 ms |

That nothing is dominated is the result, not a failure to find one. Owner
clarifications are **counted, never priced**: what it costs to interrupt an owner
depends on whether they are under a car or at a desk, and putting a dollar figure
on it would decide the trade-off by assumption rather than by evidence.
D/E/F are excluded from the dominance comparison entirely — NaN compares `False`
against everything, so leaving an unmeasured profile in would let it join the
Pareto front *by virtue of not having been measured*.

## 10. The low-evidence region

The region below `MIN_BUSINESS_EVIDENCE = 3`, where production declines to route
on the heuristic. This is where the architecture actually needs help.

| | Validation-v2 | Frozen |
|---|---|---|
| Share of traffic | **43.5%** (80/184) | 10.0% (19/191) |
| No candidate at all | 41 | 3 |
| Heuristic accuracy | 13.8% | 15.8% |
| TF-IDF accuracy | 36.2% | 31.6% |
| Embedding accuracy | **50.0%** | 26.3% |

Both fallbacks roughly double or triple the heuristic here. On validation the
embedding model is clearly strongest; **on frozen it is not** — see §12.

**Accuracy by stress axis (validation) shows the three routers are
complementary, not ranked:**

| Stress axis | n | Heuristic | TF-IDF | Embedding |
|---|---|---|---|---|
| misleading_noun | 17 | **76.5%** | 70.6% | 58.8% |
| short_command | 14 | 78.6% | 78.6% | 78.6% |
| subject_intent_mismatch | 10 | **70.0%** | 60.0% | 70.0% |
| high_evidence | 34 | 64.7% | 64.7% | **73.5%** |
| typo | 14 | 14.3% | **71.4%** | 42.9% |
| long_context | 15 | 33.3% | 26.7% | **73.3%** |
| ambiguous | 9 | 22.2% | 33.3% | **66.7%** |
| novel_phrasing | 28 | 32.1% | 50.0% | **57.1%** |
| department_boundary | 15 | 33.3% | **53.3%** | 40.0% |
| zero_evidence | 14 | 28.6% | 50.0% | 50.0% |
| multi_intent | 9 | **44.4%** | 33.3% | 22.2% |

This is the most actionable table in the report. The heuristic's hand-written
disambiguation rules genuinely win on `misleading_noun` — a business noun owned
by one department inside a task belonging to another — which is precisely what
Milestone 4 built them for. TF-IDF's character n-grams own `typo`. Embeddings own
`long_context` and `ambiguous`. **No single router dominates**, and `multi_intent`
defeats all three.

## 11. Revisiting MIN_BUSINESS_EVIDENCE

Swept on validation only (`policy.evidence_floor_sweep`):

| Floor | Heuristic share | Heuristic acc | Fallback share | Fallback acc | End-to-end |
|---|---|---|---|---|---|
| 0–1 | 77.7% | 60.8% | 22.3% | 34.2% | 54.9% |
| 2 | 74.5% | 62.8% | 25.5% | 31.9% | 54.9% |
| **3 (current)** | 56.5% | 73.1% | 43.5% | 36.2% | **57.1%** |
| 4 | 51.6% | 74.7% | 48.4% | 39.3% | 57.6% |
| 5 | 46.7% | 79.1% | 53.3% | 38.8% | 57.6% |
| 6 | 39.7% | 79.5% | 60.3% | 42.3% | 57.1% |
| 8 | 35.3% | 78.5% | 64.7% | 44.5% | 56.5% |

**Recommendation: keep `MIN_BUSINESS_EVIDENCE = 3`.** Floors of 4 and 5 score
57.6% against 3's 57.1% — a gain of **0.5 percentage points, which on 184 cases
is one case**. Moving a production constant on one case, measured on a split of
hand-written sentences, is fitting the threshold to the split. The curve is also
flat and single-peaked across 3–6, which says the current value sits inside the
plateau rather than on a cliff.

## 12. Frozen results — one run, after development

Routing-only accuracy (`milestone6-test.json`, 191 department-labelled cases).
These figures **exactly reproduce** Milestone 5's `comparison-test.json`, which is
the reproducibility check:

| Router | Accuracy | Macro F1 | Top-2 |
|---|---|---|---|
| Heuristic | 75.4% | 0.6786 | 82.7% |
| TF-IDF | 72.8% | 0.6614 | 85.9% |
| Embedding | 63.3% | 0.5775 | 76.4% |
| C: heuristic → TF-IDF | **77.0%** | 0.6773 | 85.9% |
| C2: heuristic → embedding | 76.4% | **0.7141** | 85.3% |
| G: heuristic → TF-IDF → ask | 74.4% | 0.7067 | — |

**End-to-end action benchmark** (215 cases, through `runOrchestration`,
`acceptable_departments` credit applied). This is the measure Milestone 5's
headline "85.1%" refers to, and it is **not** the same number as routing-only
accuracy above — the two must never be compared with each other:

| Architecture | Dept | Behavior | Tool | Params | Missed | **Unsafe** |
|---|---|---|---|---|---|---|
| Baseline (shipped) | 80.5% | 80.0% | 66.7% | 70.1% | 29.8% | **0/59** |
| **C: heuristic → TF-IDF** | **85.1%** | **85.6%** | **67.9%** | 70.1% | **26.2%** | **0/59** |
| C2: heuristic → embedding | 84.2% | 85.1% | 66.7% | 70.1% | 26.2% | **0/59** |
| G: heuristic → TF-IDF → ask | 81.4% | 82.8% | 66.7% | 70.1% | 26.2% | **0/59** |

**Unsafe actions: 0 of 59 on every architecture.** The safety invariant held.

### The finding that matters most: the ordering flipped

| | Validation-v2 | Frozen |
|---|---|---|
| Embedding standalone | 60.3% | 63.3% |
| TF-IDF standalone | 54.9% | 72.8% |
| **C2 (heur→embedding)** | **63.0%** | 76.4% |
| **C (heur→TF-IDF)** | 57.1% | **77.0%** |

On validation, C2 beat C by 5.9 points and the embedding model beat TF-IDF by
5.4. **On frozen, both orderings reverse.** End-to-end, C beats C2 by 0.9 points.

The honest reading is that **C and C2 are indistinguishable**, and that the
validation split's preference for the embedding model did not generalise. Had
Milestone 6 selected C2 on validation evidence and shipped it, the frozen run
would have shown that selection to be worth nothing — which is the entire reason
the frozen split is run once, at the end, and never tuned against.

### Replication against an independently authored split (added 2026-08-30)

After this milestone was pushed, PR #696 landed `validation-v3` on `main` — a
**208-case Milestone-6 validation split authored independently of this branch**,
balanced at 26 cases per department, and (by convergent design) also carrying a
`stress` axis. It shares **zero asks** with validation-v2 under all five leakage
detectors, and is clean against both `train` and the frozen split.

Two independently authored splits addressing the same milestone is a replication
opportunity that did not exist when §12 was written. Re-running the frozen
candidates against v3 changes the reading of the ordering flip substantially:

| Router / architecture | v2 (this branch) | **v3 (independent)** | Frozen |
|---|---|---|---|
| Heuristic | 47.3% | 36.5% | **75.4%** |
| TF-IDF | 54.9% | 51.9% | 72.8% |
| Embedding | 60.3% | 51.4% | 63.3% |
| C: heuristic → TF-IDF | 57.1% | 48.1% | **77.0%** |
| **C2: heuristic → embedding** | **63.0%** | **51.9%** | 76.4% |
| B: TF-IDF only | 54.9% | **51.9%** | 72.8% |

**C2 ≥ C on both hand-written splits, and C > C2 on frozen.** The disagreement
is not an artefact of one author's case-writing: it reproduces on a split
written by someone else, with no shared vocabulary.

#### The mechanism: a distribution shift, not noise

| Split | Share below `MIN_BUSINESS_EVIDENCE` | No candidate at all |
|---|---|---|
| validation-v2 (this branch) | 43.5% (80/184) | 41 |
| **validation-v3 (independent)** | **45.7% (95/208)** | 43 |
| **Frozen (action-eval-v1)** | **10.0% (19/191)** | 3 |

Both stress splits put ~45% of traffic in the region where the heuristic is
nearly useless (15.8% accuracy on v3) and the statistical models carry the load.
The frozen benchmark puts **10%** there. That single structural difference
explains the flip: frozen is dominated by high-evidence asks where the
heuristic's hand-written rules win outright, so a cascade that defers to the
heuristic (C) looks best; the stress splits are dominated by low-evidence asks,
so the stronger fallback (C2) looks best.

Two consequences, and the second is uncomfortable:

1. **The Milestone 6 recommendation is unchanged and now better supported.** C
   and C2 are not separable on the evidence available; which one leads is
   decided by the evidence mix of whichever split you measure on, not by either
   being a better router.
2. **Neither split's mix is known to match production.** Both stress splits were
   written to oversample hard cases and succeed at it; the frozen split was
   written to sample the product surface. Real tenant traffic has never been
   measured, so the honest statement is that **the correct architecture depends
   on a distribution nobody in this project has yet observed** — which raises
   the priority of instrumenting production routing (`RouterDecision` logging)
   alongside measuring Model D.

#### The calibrator choice does not fully replicate

| Router | v2 chose | v3 chose |
|---|---|---|
| TF-IDF | temperature | **temperature** ✓ |
| Heuristic | identity | **isotonic** ✗ |

TF-IDF's temperature scaling replicates cleanly. The heuristic's does not: v2
rejected isotonic on an overfit gap of 0.0861, while on v3 its gap is 0.0493 —
which slips under the 0.05 rejection bar by four thousandths and is therefore
selected. A rule that flips on a margin that thin is not measuring a stable
property. **Treat the heuristic's calibrator as undetermined at n ≈ 200**, keep
its raw confidence, and revisit only with substantially more data. The TF-IDF
result is the one that survives replication.

Reproduce:

```bash
git show origin/main:agent-service/evals/datasets/validation/validation-v3.json > /tmp/validation-v3.json
python ml/routing/milestone6.py --split validation --validation-path /tmp/validation-v3.json \
  --out ml/routing/artifacts/milestone6-validation-v3-replication.json
```


## 13. The unified RouterDecision

`agent-service/src/agent-os/agents/_router_decision.ts` (engine) and
`ml/routing/decision.py` (experiment).

```
department              chosen department, or null when the router abstained
source                  heuristic | ml | haiku | owner_clarification
raw_score               the deciding source's OWN number, on its OWN scale
calibrated_confidence   fitted P(correct), or null where no calibrator exists
alternates              runners-up, for the clarification prompt
abstained               true when no department was chosen
escalation_reason       why control left the previous stage
stages_used             which sources were consulted, in order
stage_scores            each consulted source's number, kept separate
```

Two design rules, both tested:

- **`raw_score` is never overwritten by `calibrated_confidence`.** They answer
  different questions — "how much evidence did this stage have" versus "how often
  is this stage right when it says that" — and collapsing them is how a system
  loses the ability to explain itself. `calibratedConfidence: null` is a
  meaningful value and must not fall back to the raw number, because a threshold
  will eventually be written against whatever is in that field.
- **`stage_scores` keeps every consulted source's number separately**, which is
  what makes *"the heuristic was confident and wrong"* distinguishable from
  *"the heuristic was silent"*. Those have different fixes.

**Status: the shape exists and is populated from the shipped `Classification`.
The multi-stage cascade that would fill `stages_used` with more than one entry is
measured in `ml/routing/` and is not wired into production.**

## 14. Safety boundary

Nothing in this milestone moved authorization, action risk, approval
requirements, tenant isolation, destructive-action refusal, tool permissions,
execution, or verification into a learned model.

- `setRoutingProvider` changes routing and nothing else. The action executor
  never consults it.
- `none` is excluded from the label space (`datasets.DEPARTMENTS`), so no model
  can express an opinion about out-of-scope or destructive asks.
- `RouterDecision` carries no policy field, and a test asserts the absence of
  each one by name.
- A maximally confident decision has the same shape, and buys the same
  authority, as a minimally confident one: which of eight departments drafts a
  reply.
- **Unsafe actions: 0/59 on all four frozen architectures**, and **0/21 on the
  21 safety-labelled cases in validation-v2**, which includes eight new
  adversarial cases (blanket pre-approval, forged system turn, credential
  exfiltration, cross-tenant read, bulk send, urgency pressure, and two
  destructive asks) that no earlier split contained.

## 15. Production recommendation

### **Option 6 — do not change production routing yet.**

The reasoning, in order of weight:

1. **The comparison that decides the question has never been run.** Production
   routes with Haiku when keyed. Every number in this report describes the
   offline path. Recommending a switch *from* Haiku *to* a cascade whose
   advantage over Haiku is unmeasured would be a recommendation made from
   absence of evidence.
2. **The validation→frozen ordering flip (§12) is a live warning, and it
   replicates.** The split built specifically to discriminate picked C2; an
   independently authored split (`validation-v3`, PR #696) also picked C2; the
   frozen split picked C. The flip is now traced to a measured distribution
   shift — ~45% of both stress splits sit below the evidence floor against 10%
   of the frozen split — which means the winner is decided by the evidence mix
   of the split, not by either cascade being better. Production's own mix has
   never been observed, so there is no stable winner to promote.
3. **The one gain that IS solid does not require a routing change.**
   C's +4.6 points of end-to-end department accuracy over baseline
   (80.5% → 85.1%) at $0 and ~+1.4 ms of p95 routing latency is real, reproduced
   twice, and safety-neutral — but it is
   an improvement to the *fallback* path, and shipping it is a production change
   that should be made on its own evidence, after Model D is measured, not folded
   into a milestone whose brief says measurement comes first.

**C (heuristic → TF-IDF) is the leading candidate** and the one to carry forward.
It is not being deployed here.

| Criterion | Baseline | C | Verdict |
|---|---|---|---|
| End-to-end dept accuracy | 80.5% | 85.1% | C, +4.6 pp |
| Behaviour accuracy | 80.0% | 85.6% | C, +5.6 pp |
| Missed-action rate | 29.8% | 26.2% | C, −3.6 pp |
| Cost | $0 | $0 | tie |
| p95 routing latency | 0.30 ms | 1.70 ms | baseline, +1.4 ms |
| Owner clarification | 1.6% | 0.0% | C |
| Unsafe actions | 0/59 | 0/59 | tie |
| **Beats production Haiku?** | — | **unmeasured** | **blocking** |

On latency: the +1.4 ms is TF-IDF inference on the 10% of frozen traffic that
falls through the evidence floor, measured at the routing step. End-to-end p95
across the four frozen runs sits between 1.45 ms and 1.83 ms with no consistent
ordering — at 215 in-process cases that spread is run-to-run noise, so the
routing-step figure is the one quoted. Either way it is immaterial beside the
composer and the eventual network call.

**Architecture G is not recommended for default use** but should stay available:
it is the only measured option that can say "I don't know". Its 29.3% validation
clarification rate is too high to enable globally; the sweep in §8 is the table
to revisit if a tenant ever wants a low-risk, high-friction mode.

### Failure modes of the recommendation

- If Haiku turns out to be worse than C, the delay costs real accuracy.
- **The frozen split's independence is finite and declining.** It has now been
  read by Milestone 4, twice by Milestone 5, and by this milestone — plus one
  additional re-run here after a refactor of `to_predictions`, which produced
  byte-identical metrics and therefore carried no new information about the
  split. Every read is disclosed; none of them fed a threshold, a calibrator or
  a model fit. But the count only goes up, and at some point the honest move is
  to retire it and author a second frozen set.
- Both fallbacks are trained on 1,216 synthetic examples from ~200 templates.
  Nothing here shows they survive real tenant traffic.

## 16. Limitations

1. **Model D is unmeasured.** The single largest gap. Everything about
   LLM-versus-local routing in this report is a cost figure, not a quality one.
2. **184 validation cases, hand-written by one author, from one fixture
   business.** An auto-repair shop in Phoenix. Vocabulary from a different
   vertical could reorder every result.
3. **Calibrators are fitted on 184 points.** Cross-fitting makes the reported
   numbers honest; it does not make the fit robust. Isotonic was rejected on
   exactly this ground.
4. **The heuristic keeps uncalibrated confidence**, and its worst reliability bin
   is off by 0.334 on 9 cases (§7).
5. **The abstention encoding is a modelling choice.** G's owner-clarification arm
   is expressed to the harness as two tied candidates, which the orchestrator's
   existing `isAmbiguous` turns into `needs_clarification`. That is a faithful
   use of the production path, not a change to it — but it is an encoding, and
   `export_cascade.py` documents it.
6. **Probability-to-evidence rescaling.** Feeding a fallback's probability into
   an orchestrator that thresholds raw keyword evidence requires a scale map
   (`SCORE_SCALE = 12.0`). A probability of 0.4 and a keyword score of 4 are not
   the same kind of number.
7. **The frozen split's `none` cases are excluded from routing metrics** by
   design, so routing accuracy is over 191 of 215 cases while end-to-end metrics
   are over all 215.
8. **validation-v2's behaviour labels are weaker than its department labels.**
   The split was authored to stress *routing*, and its `expected_behavior` values
   — particularly the frequent `clarification` — are the author's judgement about
   what a well-behaved system *should* do with an under-specified ask, not a
   contract validated against a shipped implementation. Run end to end, v2 scores
   49.0% department and 35.5% behaviour; the department figure is the one this
   milestone relies on. **The frozen split remains the authority on behaviour,
   tool and parameter correctness**, and every end-to-end claim in §12 is measured
   there. Tightening v2's behaviour labels is worth doing before it is used to
   select anything other than a router.

## 17. Recommended Milestone 7

**Measure Model D. Nothing else should come first.**

Concretely, and in this order:

1. **Run the committed Haiku benchmark** on validation-v2 and the frozen split.
   Cost: ~$0.20 + ~$0.24. Every other question in this report is downstream of
   the answer.
2. **Measure whether Haiku's self-reported confidence means anything** (§7 of the
   brief, deferred here for lack of a credential). Bin it and report actual
   accuracy per bin. If it is not calibrated, say so and do not threshold on it.
3. **Then decide between C and the status quo** with both sides measured, and
   evaluate E and F end-to-end — F escalates only 4.7% of frozen traffic, so an
   LLM stage may be affordable precisely because it is rarely reached.
4. **Instrument production routing before deploying anything.** The replication
   above shows the architecture choice is decided by a split's evidence mix, and
   production's mix has never been observed. `RouterDecision` logging — evidence
   score, source, and whether the ask fell below the floor — answers that from
   real traffic in a week, costs nothing, and changes no behaviour. It should
   land *before* a router change, not alongside one.
5. **Only after that, consider deployment.**

**Already in flight elsewhere.** PRs #698 / #701 / #702 / #703 ("Haiku vs H"
measurement runner, no fallback; unsafe-action measurement; send/L2
claim-then-execute via a fake Gmail port) are building exactly step 1. This
milestone's harness (`evals/export-llm-predictions.ts`, driven by
`ml/routing/milestone6.py`) and its three splits are available to that work, and
the two should be reconciled rather than run in parallel.

Deferred deliberately, and still deferred: RAG, computer use, Calendar, SMS,
active learning, fine-tuning, reinforcement learning, drift monitoring.

---

## Reproducing this

```bash
python ml/routing/authoring/build_validation_v2.py   # regenerate validation-v2
python ml/routing/leakage.py                         # 5-detector leakage report
python ml/routing/milestone6.py --split validation   # calibration + cascades
python ml/routing/milestone6.py --split test         # FROZEN — once
python ml/routing/export_cascade.py --arch C --split test
cd agent-service && node --experimental-strip-types evals/run-action-eval.ts \
  --router ../ml/routing/artifacts/router-m6-C-test.json

python -m pytest ml/routing/tests -q                 # 24 tests
cd agent-service && npm test                         # includes RouterDecision tests
```

**Environment:** Python 3.12.3 · scikit-learn 1.9.0 · numpy 2.5.2 · Node 22.22.2
· seed 20260829 · Linux 6.18.44.
**Data versions:** train `routing-train-v1` (1,216) · validation
`action-eval-validation-v2` (200) · test `action-eval-v1` (215).
**Constants:** `MIN_BUSINESS_EVIDENCE = 3.0` · `RESOLUTION_RATIO = 0.85` ·
`TFIDF_ESCALATION_CONFIDENCE = 0.40` · `ABSTAIN_BELOW_CALIBRATED = 0.55` ·
calibration folds 5.
**Calibrators:** heuristic → identity; TF-IDF → temperature, `T = 0.2`,
selected on validation, refitted on all of validation, applied once to the
frozen split.
**Artifacts:** `ml/routing/artifacts/milestone6-{validation-v2,test}.json`,
`end-to-end-frozen.json`, `e2e/frozen-{baseline,C,C2,G}.json`,
`router-m6-{C,C2,G}-test.json`.
