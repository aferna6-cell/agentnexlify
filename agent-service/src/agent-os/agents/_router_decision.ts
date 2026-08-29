/**
 * One routing decision, in a shape that can be audited after the fact.
 *
 * The engine already returns a `Classification` — a classifier label and a list
 * of candidates. That is enough to route and not enough to explain a route.
 * When a request reaches the wrong department, "the classifier said sales" does
 * not distinguish between three different failures with three different fixes:
 *
 *   the heuristic was confident and wrong    -> a scoring rule is miscalibrated
 *   the heuristic was silent and a model guessed -> the fallback is the weak link
 *   both were uncertain and nobody escalated -> the policy is wrong, not a model
 *
 * `RouterDecision` records which of those happened. It is the normalised form
 * every routing source maps onto, so a heuristic route, a statistical route and
 * an LLM route can be logged, compared and audited through one shape without
 * anyone having to remember which source produces which kind of number.
 *
 * ## Two confidences, never merged
 *
 * `rawScore` is the deciding source's own number on its own scale: keyword
 * evidence for the heuristic, a class probability for a statistical model, a
 * self-report for an LLM. These are not comparable with each other, and this
 * type deliberately does not pretend they are.
 *
 * `calibratedConfidence` is the comparable one: the fitted estimate of
 * P(this route is correct), or `null` where no calibrator has been fitted for
 * that source. `null` is a meaningful value here and must not be defaulted to
 * `rawScore` — a raw number wearing a calibrated label is worse than an
 * admitted absence, because a threshold will eventually be written against it.
 *
 * ## What a RouterDecision does NOT confer
 *
 * A department, and nothing else. Approval requirements, risk level, tool
 * selection, tenant scope, verification and destructive-action refusal are
 * decided by the action executor and the orchestrator's own policy checks,
 * neither of which reads this type. A decision carrying
 * `calibratedConfidence: 1.0` buys exactly what one carrying `0.01` buys:
 * which of eight departments drafts the reply. Confidence is not authority.
 *
 * Status: this is the observable shape, populated from the existing
 * `Classification` by `fromClassification`. The cascade that would populate
 * `stagesUsed` with more than one entry is measured in `ml/routing/` and is
 * NOT wired into production routing — Milestone 6 selects an architecture; it
 * does not deploy one.
 */

import type { Candidate, Classification } from "./_classifier.ts";

/** Where a routing decision actually came from. */
export type RoutingSource =
  /** The deterministic keyword/semantic scorer in `_classifier.ts`. */
  | "heuristic"
  /** A statistical classifier registered through `setRoutingProvider`. */
  | "ml"
  /** The production Haiku router. */
  | "haiku"
  /** No source would decide; the owner is being asked. */
  | "owner_clarification";

/** Why control left a stage. Absent when the first stage decided. */
export type EscalationReason =
  /** Top candidate scored below `MIN_BUSINESS_EVIDENCE`. */
  | "heuristic_below_floor"
  /** No department scored at all. */
  | "heuristic_no_candidate"
  /** The fallback's calibrated confidence was under the abstention bar. */
  | "fallback_below_confidence"
  /** The model returned nothing usable — unparseable, or an unmappable id. */
  | "source_unavailable"
  /** Top two were too close to separate (`isAmbiguous`). */
  | "candidates_indistinguishable";

export interface RouterDecision {
  /** The chosen department, or null when the router abstained. */
  department: string | null;
  source: RoutingSource;
  /**
   * The deciding source's own number, on its own scale. Never overwritten by
   * the calibrated value: the two answer different questions and collapsing
   * them is how a system loses the ability to explain itself.
   */
  rawScore: number | null;
  /**
   * Fitted P(correct), or null where this source has no calibrator. Null is a
   * real value. Do not fall back to `rawScore`.
   */
  calibratedConfidence: number | null;
  /** Runners-up, in order. Feeds the clarification prompt. */
  alternates: Candidate[];
  /** True when no department was chosen and the owner is being asked. */
  abstained: boolean;
  escalationReason: EscalationReason | null;
  /** Which sources were consulted, in order. */
  stagesUsed: RoutingSource[];
  /**
   * Each consulted source's own number, kept separately and never merged.
   * This is what makes "the heuristic was confident and wrong" distinguishable
   * from "the heuristic was silent".
   */
  stageScores: Record<string, number>;
}

/**
 * Build the observable decision from what the shipped classifier returned.
 *
 * Single-stage by construction, because production routing is currently
 * single-stage. `stagesUsed` is a list rather than a scalar so that a cascade
 * can populate it without changing the type, and so that a log written today
 * stays readable if one ever ships.
 */
export function fromClassification(cls: Classification): RouterDecision {
  const top = cls.candidates[0];
  const source: RoutingSource = cls.classifier === "haiku" ? "haiku"
    : cls.classifier === "ml" ? "ml"
    : "heuristic";

  if (!top) {
    return {
      department: null,
      source: "owner_clarification",
      rawScore: null,
      calibratedConfidence: null,
      alternates: [],
      abstained: true,
      escalationReason: "heuristic_no_candidate",
      stagesUsed: [source],
      stageScores: {},
    };
  }

  // The heuristic's meaningful number is raw evidence; `confidence` is a
  // saturating transform of it and is what the orchestrator explicitly does NOT
  // threshold on. Every other source reports a probability directly.
  const raw = typeof top.score === "number" ? top.score : top.confidence;

  return {
    department: top.agentId,
    source,
    rawScore: raw,
    // Nothing in the engine is calibrated today. Reporting null is the accurate
    // statement; Milestone 6 fitted calibrators offline and did not ship them.
    calibratedConfidence: null,
    alternates: cls.candidates.slice(1),
    abstained: false,
    escalationReason: null,
    stagesUsed: [source],
    stageScores: { [source]: raw },
  };
}

/**
 * Fold an ambiguity-driven clarification into the same shape.
 *
 * The orchestrator already has this path (`isAmbiguous` -> `needs_clarification`).
 * Representing it as a `RouterDecision` means the abstention rate can be read
 * off the same log as everything else, rather than inferred from a status
 * string in a different table.
 */
export function asClarification(cls: Classification, reason: EscalationReason): RouterDecision {
  const base = fromClassification(cls);
  return {
    ...base,
    department: null,
    source: "owner_clarification",
    abstained: true,
    escalationReason: reason,
    alternates: cls.candidates.slice(0, 2),
  };
}
