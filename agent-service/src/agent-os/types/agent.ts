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
  status: string;
  reviewRequested: boolean;
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

/** Everything an agent may read. Mirrors the production data layer. */
export interface SharedContext {
  businessProfile: BusinessProfileData;
  widgetHistory: WidgetConversationData[];
  pipelineLeads: PipelineLeadData[];
  appointments: AppointmentData[];
  invoices: InvoiceData[];
  agentRunHistory: AgentRunHistoryItem[];
  kb: KbEntry[];
  /** Eval / FastAPI may attach a tenant-scoped corpus. Never another tenant. */
  ragCorpus?: RagChunk[];
  ragEvidence?: RagEvidenceItem[];
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
