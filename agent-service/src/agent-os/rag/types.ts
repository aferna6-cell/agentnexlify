export interface RagChunk {
  chunk_id: string;
  document_id: string;
  account_id: string;
  title: string;
  section: string;
  content: string;
  source_type: string;
  citation_label: string;
  status?: string;
}

export interface RagEvidence {
  chunkId: string;
  documentId: string;
  accountId: string;
  title: string;
  section: string;
  content: string;
  sourceType: string;
  score: number;
  citationLabel: string;
}

export interface RetrievalResult {
  evidence: RagEvidence[];
  abstain: boolean;
  reason: string;
}
