# Decision pipeline — error analysis and generalization fixes

Milestone 4. Baseline commit `9c3ac4a`. Method: build a stage-based error
taxonomy, fix root causes at the category level against the **editable
validation split**, then run the frozen test split **once** to measure whether
the fixes generalized.

No production rule in this change was written against a frozen-test sentence.

---

## 1. Validation baseline and taxonomy

`npm run eval:errors` attributes every failure to the earliest pipeline stage
that caused it. A run that routed to the wrong department and therefore took no
action is **one routing failure**, not three — counting each symptom separately
would have made routing look a third as important as it is and sent the first
fix to the wrong place.

Validation split at `9c3ac4a`, 35 cases, 20 failing:

| Stage | Failures | % of failures |
|---|---|---|
| routing | 13 | 65.0% |
| action_resolution | 4 | 20.0% |
| intent_behavior | 1 | 5.0% |
| context_resolution | 1 | 5.0% |
| skill_selection | 1 | 5.0% |

29 downstream symptoms were attributed upstream rather than counted again.

Eight of the thirteen routing failures scored **zero** department candidates.
`"Email sarah.chen@example.com that her car is ready for pickup"` matched no
department at all.

---

## 2. Root causes

### 2.1 Routing signals were derived only from drafting skills

`defineDepartment` built a department's routing surface from the union of its
skills' keywords. Customer Data & Administration owns `add_customer_note`, but
its skills are a document drafter and a content writer — so every routing signal
it had described document authorship. **The department was unreachable for
record mutation, not because the capability was missing, but because nothing in
the routing surface mentioned it.** `resolveAction` was invisible to routing.

### 2.2 Task intent and business subject were the same axis

The classifier scored business-subject keywords only. There was no
representation of what the owner wanted *done*. Consequences:

- `"Note on Mike's record that he approved the tire quote"` scored as a Sales
  task, because `quote` is a Sales signal and nothing represented "putting a
  note on a record".
- `"Email X and see if she still wants that brake quote"` reached Sales
  correctly, then `quote_generator` won the intra-department scoring on the same
  word and refused with `no line items provided`. No draft meant
  `resolveActionFromOutput` had nothing to convert, so the send was never
  proposed. **A skill that declined to compose could silently veto an action the
  owner had clearly authorized.**

### 2.3 Sending was a Sales capability rather than a system one

`resolveActionFromOutput` was wired into Sales alone. Operations would compose a
correct "your car is ready" message to an address the owner had written out in
full, then hand it back as a draft. This single defect accounted for most of the
92.9% missed-action rate.

### 2.4 The ambiguity test was not scale-invariant

`confidence = score/(score+2)` saturates, so the same one-point lead reads as
0.17 between weak candidates and 0.02 between strong ones. An absolute 0.1 gap
test therefore re-labelled well-separated pairs "ambiguous" as soon as scores
grew — the owner saw *"which department did you mean?"* for requests the system
understood exactly. Latent before this milestone; the semantic scores exposed it
immediately.

### 2.5 A department could not ask a question

The orchestrator had a `needs_clarification` status for its own routing ties, but
a department that needed one more detail could only return "no draft". To the
owner that reads as a refusal.

### 2.6 Subject nouns were conflated with sentiment and with plurals

`detectComplaint` treated `refund` as complaint language, so an owner's
instruction to issue one — a billing task — was short-circuited into complaint
handling. Separately, `\bappointment\b` did not match `appointments`, so
`"remind tomorrow's appointments"` lost its subject entirely.

---

## 3. Architectural changes

Four new seams, all pure and independently testable.

### `agents/_intent.ts` — task intent, separated from business subject

Parses an ask onto four independent axes:

| Axis | Question | Values |
|---|---|---|
| `intent` | what to do | communicate / create / update_record / retrieve / schedule / analyze / destroy |
| `subjectType` | what it is about | quote / invoice / appointment / customer_record / … |
| `channel` | how it goes out | email / sms / phone / none |
| `authorization` | who performs it | execute / draft_only / ambiguous |

`authorization` is its own axis rather than a property of the verb. *"Draft an
email to Sarah"* and *"Email Sarah"* share an intent and a channel and differ
only in who presses send — a permission question, which belongs next to the
approval model rather than inside a keyword list. `draft_only` wins every tie:
an owner who asked for words is never surprised by a send.

Two rules do most of the work:

- **You cannot create what already exists.** `subjectExists` (`"the quote we
  sent"`, `"about the brake quote"`) forces `communicate`, which is what keeps
  communication requests out of generative skills.
- **A question is never the act it describes.** *"Should I be noting quote
  approvals?"* is analysis; *"Note that he approved"* is a record mutation.

### `agents/_resolve.ts` — one entity-resolution seam

Name matching previously existed in three places with three different answers
(`includes`, `startsWith`, and id-then-exact-then-prefix). Now one function
returns a discriminated outcome — `exact` / `unique` / `multiple` / `none` — so
**ambiguity is a value the caller must handle rather than a `null` it can
mistake for "no match"**. Tiers never mix: two exact duplicates stay ambiguous
rather than falling through to a looser rule that would appear to break the tie.
Whole-word matching stops `"Mike"` matching `"Carmike"`.

There is no confidence threshold that makes choosing between two real customers
acceptable, so none is offered.

### Departments declare semantics, not just skills

```ts
semantics: {
  subjects: ["customer_record", "document"],
  intents: ["update_record", "retrieve", "create", "destroy"],
  primaryIntents: ["update_record"],   // exclusively owned
}
```

A department is now reachable for **what it can do**, not only for what its
skills can write. `primaryIntents` is a claim of exclusivity — no other
department mutates customer records — and is weighted to dominate rather than
merely to lead, because a score another department's keyword pile can approach
turns that claim into a coin-flip the orchestrator asks the owner to settle.

Skills declare `servesIntents` and `generative`, so a quote generator is
*ineligible* for a communication request however well the word "quote" scores.

### Sending became a system capability

`sales_actions.ts` → `communication_actions.ts`, wired into Sales, Operations,
Invoicing, Customer Service and Marketing. Whether a message can be sent depends
on the message and the owner's authorization, not on which department wrote it.
The safety rules are unchanged and now apply uniformly: the address must be
written in the owner's own ask, and `authorizesAction` must be true.

### Supporting fixes

- Action resolution moved **before** composition, so a skill that declines to
  compose can no longer veto an authorized action.
- `isAmbiguous` measures relative margin on raw evidence.
- `AgentOutput.needsClarification` lets a department ask a question and have the
  owner see a question.
- Destructive asks and asks about the system's own internals or credentials are
  declined centrally, honestly, before any department is selected.

---

## 4. Validation results

| Metric | Before | After |
|---|---|---|
| Department accuracy | 62.9% | **97.1%** |
| Behavior accuracy | 54.3% | **97.1%** |
| Tool accuracy | 0.0% | **100%** |
| Parameter exact match | 0.0% | **100%** |
| Missed-action rate | 81.8% | **0.0%** |
| Unsafe actions | 0 / 31 | **0 / 31** |

Change log, each measured on validation before moving on:

| Change | Hypothesis | Stage | Dept | Behavior | Tool | Safety |
|---|---|---|---|---|---|---|
| — | baseline | — | 62.9 | 54.3 | 0.0 | clean |
| intent axis + semantics + intent-gated skills | routing/skill-contract | routing, skill_contract | 62.9 | 45.7 | 27.3 | clean |
| scale-invariant ambiguity | spurious clarification | routing | 62.9 | 45.7 | 27.3 | clean |
| exclusive ownership decisive | routing ties | routing | 65.7 | 48.6 | 36.4 | clean |
| inbound/outbound split | routing | routing | 74.3 | 51.4 | 54.5 | clean |
| plurals, question-shaped drafts, marketing comms | routing | routing | 80.0 | 68.6 | 54.5 | clean |
| department clarification surfaced | intent_behavior | intent_behavior | 88.6 | 74.3 | 54.5 | clean |
| meta-ask decline, subject precedence, complaint sentiment | routing, safety | routing | 88.6 | 74.3 | 54.5 | clean |
| destroy decline, topic reference, evidence floor | intent_behavior | intent_behavior | 85.7 | 80.0 | 54.5 | clean |
| **sending as a system capability** | action_resolution | action_resolution | 85.7 | 88.6 | **90.9** | clean |
| create-vs-exists, complaint scoring, draft-only ambiguity | intent, routing | mixed | 88.6 | 91.4 | 90.9 | clean |
| read-only retrieve path | skill_selection | skill_selection | 88.6 | 94.3 | 100 | clean |
| three validation labels corrected (§7) | label correctness | — | 97.1 | 94.3 | 100 | clean |
| coverage gaps found by category tests | intent | intent | 97.1 | 97.1 | 100 | clean |

Safety was clean at every step. No change was kept that moved accuracy at the
cost of a safety violation, because none occurred.

---

## 5. Frozen test results — one run, after development

`npm run eval:actions`, 215 cases, offline engine.

| Metric | Baseline `9c3ac4a` | Now | Absolute | Relative |
|---|---|---|---|---|
| Department accuracy | 51.6% | **80.5%** | +28.9 pp | +56% |
| Department top-2 | 53.5% | **83.3%** | +29.8 pp | +56% |
| Department macro F1 | 0.5804 | **0.7051** | +0.125 | +21% |
| Behavior accuracy | 45.1% | **80.0%** | +34.9 pp | +77% |
| Tool accuracy | 3.6% | **66.7%** | +63.1 pp | ×18.5 |
| Approval accuracy | 100% (3 scored) | **100% (56 scored)** | — | 18× more scored |
| Parameter exact match | 3.9% | **70.1%** | +66.2 pp | ×18 |
| Parameter field-level | 3.1% | **73.2%** | +70.1 pp | ×24 |
| Missed-action rate | 92.9% | **29.8%** | −63.1 pp | −68% |
| **Unsafe actions** | **0 / 59** | **0 / 59** | **unchanged** | — |
| Latency p95 | 1.90 ms | 1.64 ms | −0.26 ms | — |

Cases fully correct on every axis: **154 / 215**, up from 44.

**No regression on any metric.** Approval accuracy stayed at 100% while the
number of scored cases went from 3 to 56, which is the more meaningful result:
the gate now has 18× as many opportunities to be wrong and is not.

### Known label disagreement, not corrected

Three frozen cases (`unsafe_003`, `unsafe_004`, `unsafe_014`) label a
destructive ask as `admin_records`; the system now declines centrally before
selecting a department, so it reports `none`. The behaviour — refuse — is
correct and safe in both readings. **The frozen labels were not edited**, and
these count as failures in the numbers above.

---

## 6. Remaining failures, by stage

Frozen split, 61 failing cases:

| Stage | Failures | % of failures | % of all cases |
|---|---|---|---|
| **routing** | **42** | **68.9%** | 19.5% |
| action_resolution | 11 | 18.0% | 5.1% |
| skill_selection | 4 | 6.6% | 1.9% |
| intent_behavior | 3 | 4.9% | 1.4% |
| context_resolution | 1 | 1.6% | 0.5% |

Routing now dominates, and its shape has changed. **24 of the 42 are "got
none"** — no department accumulated enough evidence to be a candidate at all:

```
expected sales,            got none   10
expected admin_records,    got none    7
expected customer_service, got none    3
expected marketing,        got none    2
expected accounting,       got none    2
```

This is a **recall problem in a hand-written lexicon**, not a discrimination
problem. The remaining 18 are genuine confusions between plausible departments
(`marketing → sales` ×4, `customer_service → marketing` ×2).

The 11 `action_resolution` failures are almost all "drafted instead of
proposing": asks that authorize a send but where the composed draft was empty or
the recipient was named rather than addressed.

---

## 7. Validation labels corrected, and why

Three validation labels were widened, each for a reason that stands
independently of what any implementation does. Recorded here because editing
labels after seeing failures is exactly the habit that erodes a benchmark.

1. **`v_hard_001a` / `v_hard_001b`** — *"your car is ready for pickup"* is
   service-delivery communication, which Operations owns per its own stated
   purpose (*"operational updates … order ready"*). The original label assumed
   outbound-to-a-customer is always Sales. Operations added as acceptable; both
   halves of the pair route consistently, which is what the pair tests.
2. **`v_unsafe_002`** — a destructive ask is refused system-wide before a
   department is chosen, so `none` is the honest department. Refusing centrally
   beats routing it somewhere to be refused.

`expected_department` was not changed in any case; only `acceptable_departments`
was widened. **No frozen label or ask was edited.**

---

## 8. Category-level tests

33 new tests across four files, using subjects and names that appear in **no**
benchmark case — the point is that the abstraction generalized, not that the
measured sentences work.

| File | Tests | Proves |
|---|---|---|
| `agents/_intent.test.ts` | 10 | quote/invoice/agreement/job-post all separate create from communicate; existence rules out creation; notes are record mutations whatever noun they carry; asking for words never authorizes an act; plurals |
| `agents/_resolve.test.ts` | 10 | exact/unique/multiple/none; ambiguity never falls through to a looser rule; `"Mike"` does not match `"Carmike"`; a customer known only from an invoice still resolves |
| `agents/_routing_semantics.test.ts` | 8 | record mutation reaches Admin & Records across five different subject nouns; exclusive ownership is decisive; both halves of an act/ask pair route identically |
| `agents/_action_eligibility.test.ts` | 5 | all four communicating departments propose a send and none sends on a draft-only ask; a recipient is never invented; ambiguity produces a question |

Two of these caught real generalization gaps during development — `send` was
missing from the communicate verbs, and `respond` from the message subject —
which is what a category test is for.

Engine suite: **137 tests**, up from 104. All green.

---

## 9. Recommended first ML experiment

**Department routing recall — and measure the model already shipping before
training anything new.**

The evidence:

- Routing is **68.9%** of remaining failures, 3.8× the next stage.
- **24 of 42** routing failures are zero-evidence, not misclassification. Every
  keyword and every semantic rule missed. That is precisely the failure mode a
  learned classifier fixes and a hand-written lexicon cannot: unbounded
  paraphrase.
- Every downstream stage is now under 20% of failures and mostly downstream of
  routing anyway.

The honest first step is **not** to train a model. Production already routes with
Haiku (`classifyWithHaiku`); the heuristic is only the offline fallback, and
every number in this document measures the fallback. So:

1. **Measure the LLM path on this benchmark first.** `engine.llm_backed` already
   distinguishes the two in every result file. If Haiku's recall closes the
   zero-evidence gap, the answer is that the offline fallback needs the work, not
   the product.
2. **Only if the gap persists**, train a small classifier on the `train/` split
   (still empty by design) with the frozen split held out.

Recommending an experiment against the model we already ship, rather than a new
one, is the conclusion the evidence supports.

Not recommended as first: entity resolution (1 failure), approval policy (0
failures, 56 scored), or parameter extraction (70.1%, mostly downstream of
routing).

---

## 10. Cross-references

- `docs/agent-action-eval.md` — the harness, dataset and safety gate
- `agent-service/evals/datasets/README.md` — split strategy and leakage rules
- `agent-service/src/agent-os/agents/_intent.ts` — the intent/subject split
- `agent-service/src/agent-os/agents/_resolve.ts` — the resolution seam
- `agent-service/src/agent-os/agents/communication_actions.ts` — sending as a
  system capability
