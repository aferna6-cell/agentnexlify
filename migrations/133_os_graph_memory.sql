-- 133_os_graph_memory.sql
-- Agent OS knowledge graph — the long-term memory layer deferred by ADR
-- planning/decisions/2026-05-25-agent-os-graph-memory.md and built now that
-- its revisit trigger fired (owner-requested navigable memory, 2026-06-09).
--
-- One node per (client, entity_type, normalized name): the people, jobs,
-- preferences, and decisions the OS has learned about one business. Facts
-- accumulate on the node as a capped JSONB list with provenance; edges record
-- typed relations between nodes. Extraction is one Haiku call per OWNER TURN
-- (not per memory write), which keeps the ADR's cost concern addressed.
--
-- Complements (does not replace) os_memory_entries: every extracted fact is
-- also written there for vector recall; the graph adds the entity-pivoted
-- view ("show me everything about Sarah") semantic search can't give.
--
-- RLS: deny-public (see 118 rationale) — service role + tenant_scope only.

CREATE TABLE IF NOT EXISTS os_graph_nodes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id        UUID NOT NULL,
    entity_type      TEXT NOT NULL CHECK (entity_type IN (
        'customer', 'staff', 'vendor', 'service', 'job',
        'preference', 'decision', 'place', 'other'
    )),
    name             TEXT NOT NULL,
    normalized_name  TEXT NOT NULL,               -- lower/trimmed dedup key
    summary          TEXT NOT NULL DEFAULT '',
    facts            JSONB NOT NULL DEFAULT '[]', -- [{fact, source, at}] capped in service
    mention_count    INTEGER NOT NULL DEFAULT 1,
    embedding        vector(512),                 -- voyage-3-lite over name+summary
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (client_id, entity_type, normalized_name)
);

COMMENT ON TABLE os_graph_nodes IS
    'Agent OS knowledge graph: one node per entity the OS knows about a business. Haiku-extracted per owner turn.';

CREATE INDEX IF NOT EXISTS os_graph_nodes_client_idx
    ON os_graph_nodes (client_id, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS os_graph_nodes_embedding_idx
    ON os_graph_nodes
    USING hnsw (embedding vector_cosine_ops);

ALTER TABLE os_graph_nodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_graph_nodes_deny_public"
    ON os_graph_nodes
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);

CREATE TABLE IF NOT EXISTS os_graph_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL,
    from_node       UUID NOT NULL REFERENCES os_graph_nodes(id) ON DELETE CASCADE,
    to_node         UUID NOT NULL REFERENCES os_graph_nodes(id) ON DELETE CASCADE,
    relation        TEXT NOT NULL,                -- e.g. requested, prefers, works_on, decided
    observed_count  INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (client_id, from_node, to_node, relation)
);

COMMENT ON TABLE os_graph_edges IS
    'Agent OS knowledge graph: typed relations between nodes, weight = observed_count.';

CREATE INDEX IF NOT EXISTS os_graph_edges_client_idx
    ON os_graph_edges (client_id, last_seen_at DESC);

ALTER TABLE os_graph_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_graph_edges_deny_public"
    ON os_graph_edges
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
