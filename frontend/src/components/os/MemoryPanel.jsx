/**
 * MemoryPanel - "What I know about your business."
 *
 * Renders the Agent OS knowledge graph (os_graph_nodes/edges) as entity cards
 * grouped by type, each with its accumulated facts and a Forget button
 * (owner-only on the API side). Transparency surface for long-term memory:
 * the owner sees exactly what the OS has learned and can delete any of it.
 */

import { useState, useEffect, useCallback } from "react";
import { fetchOsGraph, forgetOsGraphNode } from "../../utils/api/os";
import useIsMobile from "../../hooks/useIsMobile";

const TYPE_LABELS = {
  customer: "Customers",
  staff: "Staff",
  vendor: "Vendors",
  service: "Services",
  job: "Jobs",
  preference: "Preferences",
  decision: "Decisions",
  place: "Places",
  other: "Other",
};

export default function MemoryPanel({ token, onClose }) {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMobile = useIsMobile();

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    fetchOsGraph(token)
      .then((data) => setGraph({ nodes: data?.nodes || [], edges: data?.edges || [] }))
      .catch((err) => setError(err.message || "Failed to load memory"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const forget = (nodeId) => {
    forgetOsGraphNode(token, nodeId)
      .then(() =>
        setGraph((prev) => ({
          nodes: prev.nodes.filter((n) => n.id !== nodeId),
          edges: prev.edges.filter(
            (e) => e.from_node !== nodeId && e.to_node !== nodeId,
          ),
        })),
      )
      .catch((err) => setError(err.message || "Could not forget that"));
  };

  const grouped = graph.nodes.reduce((acc, n) => {
    const key = n.entity_type || "other";
    (acc[key] = acc[key] || []).push(n);
    return acc;
  }, {});

  return (
    <aside
      aria-label="Agent OS memory"
      style={
        isMobile
          ? {
              position: "fixed",
              inset: 0,
              width: "100%",
              zIndex: 70,
              display: "flex",
              flexDirection: "column",
              background: "var(--bg-primary)",
              minHeight: 0,
            }
          : {
              width: 340,
              flexShrink: 0,
              borderLeft: "1px solid var(--border)",
              display: "flex",
              flexDirection: "column",
              background: "var(--bg-primary)",
              minHeight: 0,
            }
      }
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 14px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div>
          <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>Memory</div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
            What the OS has learned. Forget anything, any time.
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Close memory panel"
          style={{
            border: "1px solid var(--border)",
            background: "transparent",
            color: "var(--text-muted)",
            borderRadius: 8,
            padding: "4px 10px",
            cursor: "pointer",
          }}
        >
          Close
        </button>
      </div>

      <div style={{ overflowY: "auto", padding: 12, minHeight: 0 }}>
        {error && (
          <div style={{ color: "var(--danger, #f87171)", fontSize: "0.8rem", marginBottom: 8 }}>
            {error}
          </div>
        )}
        {loading ? (
          <div style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>Loading…</div>
        ) : graph.nodes.length === 0 ? (
          <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", lineHeight: 1.5 }}>
            Nothing learned yet. As you work with your agents, the OS builds a
            memory of your customers, jobs, and preferences here.
          </div>
        ) : (
          Object.entries(grouped).map(([type, nodes]) => (
            <section key={type} style={{ marginBottom: 14 }}>
              <h4
                style={{
                  margin: "0 0 6px",
                  fontSize: "0.72rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--text-muted)",
                }}
              >
                {TYPE_LABELS[type] || type} ({nodes.length})
              </h4>
              {nodes.map((n) => (
                <div
                  key={n.id}
                  data-testid={`memory-node-${n.id}`}
                  style={{
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    padding: "8px 10px",
                    marginBottom: 6,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "baseline",
                      gap: 8,
                    }}
                  >
                    <strong style={{ fontSize: "0.82rem" }}>{n.name}</strong>
                    <button
                      onClick={() => forget(n.id)}
                      aria-label={`Forget ${n.name}`}
                      style={{
                        border: "none",
                        background: "transparent",
                        color: "var(--text-muted)",
                        fontSize: "0.72rem",
                        cursor: "pointer",
                        textDecoration: "underline",
                      }}
                    >
                      Forget
                    </button>
                  </div>
                  <div
                    style={{
                      fontSize: "0.76rem",
                      color: "var(--text-secondary, var(--text-muted))",
                      lineHeight: 1.45,
                      marginTop: 2,
                    }}
                  >
                    {n.summary}
                  </div>
                  <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginTop: 4 }}>
                    seen {n.mention_count}× · last{" "}
                    {n.last_seen_at ? new Date(n.last_seen_at).toLocaleDateString() : " - "}
                  </div>
                </div>
              ))}
            </section>
          ))
        )}
      </div>
    </aside>
  );
}
