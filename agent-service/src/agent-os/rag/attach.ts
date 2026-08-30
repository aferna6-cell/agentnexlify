/**
 * applyRagToContext — SharedContext RAG grounding contract.
 *
 * Retrieved documents are untrusted data: never system instructions,
 * never authorization, never tool policy. Abstention must be explicit.
 */

import type { SharedContext } from "../types/agent.ts";
import { ragEnabled } from "./flags.ts";
import { retrieveBusinessContext } from "./retrieve.ts";

export function applyRagToContext(
  accountId: string,
  ask: string,
  context: SharedContext,
): SharedContext {
  try {
    if (!ragEnabled()) return context;
    const corpus = context.ragCorpus ?? [];
    if (!corpus.length) {
      return {
        ...context,
        ragStatus: "abstain",
        ragAbstainReason: "no_approved_knowledge",
        ragEvidence: [],
      };
    }
    const retrieved = retrieveBusinessContext({ accountId, ask, corpus });
    if (retrieved.abstain) {
      return {
        ...context,
        ragStatus: "abstain",
        ragAbstainReason: retrieved.reason,
        ragEvidence: [],
        kb: context.kb,
      };
    }
    const evidence = retrieved.evidence.map((e) => ({
      chunkId: e.chunkId,
      documentId: e.documentId,
      accountId: e.accountId,
      title: e.title,
      citationLabel: e.citationLabel,
      content: e.content,
      score: e.score,
    }));
    const kbExtra = evidence.map((e) => ({
      topic: `rag:${e.citationLabel}`,
      answer: e.content,
    }));
    return {
      ...context,
      ragStatus: "ok",
      ragAbstainReason: null,
      ragEvidence: evidence,
      kb: [...kbExtra, ...context.kb],
    };
  } catch {
    return {
      ...context,
      ragStatus: "error",
      ragAbstainReason: "infrastructure_error",
      ragEvidence: [],
    };
  }
}
