/**
 * Shared types for the agent engine.
 */

import type { RagChunk } from "../rag/types.ts";

export interface BusinessProfileData {
  businessName?: string;
  ownerName?: string;
  industry?: string;
  /** v2: industry cluster id (e.g. "automotive") + specific type (e.g. "Tire shop"). */
  industryCluster?: string;
  businessType?: string;
  city?: string;
  state?: string;
  phone?: string;
  email?: string;
  website?: string;
  hoursSummary?: string;
  timezone?: string;
  reviewLinkGoogle?: string;
  reviewLinkYelp?: string;
  reviewLinkFacebook?: string;
  paymentLink?: string;
}

export interface WidgetConversationData {
  id: string;
  contactName?: string;
  intent?: string;
  /** Stored per-conversation tone: positive | neutral | negative. Set by the
   *  backend conversation_enrichment classifier; absent when unclassified. */
  sentiment?: string;
  summary: string;
  topics: string[];
  closedAt: string;
}

export interface PipelineLeadData {
  id: string;
  name: string;
  status: string;
  subject?: string;
  quoteAmount?: number;
  lastContactDate?: string;
  email?: string;
  phone?: string;
  address?: string;
}

export interface AgentRunHistoryItem {
  agentId: string;
  title: string;
  status: string;
  createdAt: string;
  /** Customer Question runs where the KB lacked the answer (a holding reply was
   * drafted). Surfaced by the Weekly Briefing as a "KB gap" to address. */
  kbGap?: boolean;
}

export interface AppointmentData {
  id: string;
  customerName: string;
  service?: string;
  scheduledFor: string;
  /** End time when known — used to seed calendar busy / events. */
  scheduledEnd?: string;
  status: string;
  reviewRequested: boolean;
  googleEventId?: string;
}

export interface InvoiceData {
  id: string;
  customerName: string;
  number: string;
  amount: number;
  issuedAt: string;
  dueAt: string;
  status: string;
}

export interface KbEntry {
  topic: string;
  answer: string;
}

/** Retrieved approved tenant knowledge. Optional — absent when RAG is off. */
export interface RagEvidenceItem {
  chunkId: string;
  documentId: string;
  accountId: string;
  title: string;
  citationLabel: string;
  content: string;
  score: number;
}

/**
 * RAG grounding contract on SharedContext.
 *
 * - ok: ragEvidence is authoritative approved knowledge (also mirrored into kb)
 * - abstain: retrieval ran; evidence was insufficient/untrusted/missing —
 *   agents must NOT treat this as a KB answer
 * - error: RAG infrastructure failed; distinct from successful abstention
 * - disabled / absent: RAG flag off
 */
export type RagStatus = "ok" | "abstain" | "error" | "disabled";

/** Everything an agent may read. Mirrors the production data layer. */
export interface SharedContext {
  businessProfile: BusinessProfileData;
  widgetHistory: WidgetConversationData[];
  pipelineLeads: PipelineLeadData[];
  /** Tenant pipeline stage names; empty/absent → canonical closed set. */
  pipelineStages?: string[];
  appointments: AppointmentData[];
  invoices: InvoiceData[];
  agentRunHistory: AgentRunHistoryItem[];
  kb: KbEntry[];
  /** Eval / FastAPI may attach a tenant-scoped corpus. Never another tenant. */
  ragCorpus?: RagChunk[];
  /** Authoritative retrieved evidence — only populated when ragStatus === "ok". */
  ragEvidence?: RagEvidenceItem[];
  ragStatus?: RagStatus;
  /** Set when ragStatus is abstain or error. */
  ragAbstainReason?: string | null;
  /**
   * Busy intervals for calendar availability (Google freebusy + appointments).
   * When absent and calendarAvailabilityError is unset, Collecting calendar
   * still fails closed until seeded.
   */
  calendarBusy?: { start: string; end: string }[];
  /** Honest provider failure — tools must surface, never invent free slots. */
  calendarAvailabilityError?: string | null;
}

export type Channel =
  | "sms"
  | "email"
  | "sequence"
  | "report"
  | "post"
  | "widget_reply"
  | "internal";

export interface DraftOutput {
  title: string;
  body: string;
  channel: Channel;
  metadata?: Record<string, unknown>;
  requiresApproval: boolean;
}

export interface AgentOutput {
  draft?: DraftOutput;
  /** Surfaced in the orchestrator chat — never inside the draft. */
  orchestratorNotes: string[];
  /** Set when the agent intentionally produced no draft. */
  noDraftReason?: string;
  needsClarification?: boolean;
}

/** A trace step as streamed to the client and persisted. */
export interface StreamedTraceStep {
  step: string;
  status: "completed" | "skipped_no_data" | "fallback" | "work";
  description: string;
}

/**
 * The trace emitter. `emit` is the honest-load primitive: it refuses to mark a
 * step "completed" unless the caller supplies non-empty `data`. This makes the
 * QA "false success" bug architecturally impossible to reintroduce.
 */
export interface TraceEmitter {
  /** Returns true when data was present (and the step marked completed). */
  emit(
    step: string,
    payload?: { description: string; data: unknown },
  ): Promise<boolean>;
  /** An ordinary reasoning step the agent always performs. */
  work(step: string, description: string): Promise<void>;
  /** An explicit honest fallback line (e.g. "no KB yet — using a safe reply"). */
  fallback(step: string, description: string): Promise<void>;
}

export interface AgentRunArgs {
  input: Record<string, unknown>;
  context: SharedContext;
  emitTrace: TraceEmitter;
  /** Verbatim owner ask. */
  ownerAsk: string;
  /** The current agent run id (for model-call cost association). */
  runId: string;
  /** The owner's user id, when available (for agents that tag the owner record). */
  userId?: string;
}
