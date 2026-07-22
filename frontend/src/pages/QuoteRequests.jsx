import { useCallback, useEffect, useState } from "react";

import { useAuth } from "../context/AuthContext";
import { fetchPhotoQuotes, submitQuoteFeedback } from "../utils/api/photo-quotes";

const CAP = 500;

function MetricCard({ label, value, sub, danger }) {
  return (
    <div
      style={{
        flex: 1,
        background: "var(--surface, #111827)",
        border: "1px solid var(--border, #1f2937)",
        borderRadius: 10,
        padding: 16,
      }}
    >
      <div style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>{label}</div>
      <div
        style={{
          color: danger ? "#ef4444" : "var(--text-primary)",
          fontSize: "1.4rem",
          fontWeight: 700,
          marginTop: 4,
        }}
      >
        {value}
      </div>
      {sub ? (
        <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginTop: 2 }}>
          {sub}
        </div>
      ) : null}
    </div>
  );
}

function meterColor(count) {
  if (count > CAP) return "#ef4444"; // red - over cap
  if (count >= 400) return "#f59e0b"; // yellow - approaching
  return "#22c55e"; // green
}

function UsageMeter({ usage }) {
  if (!usage) return null;
  const { quote_count = 0, overage_count = 0, overage_charge = 0 } = usage;
  const pct = Math.min(100, Math.round((quote_count / CAP) * 100));
  const color = meterColor(quote_count);
  return (
    <div
      style={{
        background: "var(--surface, #111827)",
        border: "1px solid var(--border, #1f2937)",
        borderRadius: 10,
        padding: 16,
        marginBottom: 20,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>
          This month
        </span>
        <span style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
          {quote_count} / {CAP}
          {overage_count > 0
            ? ` (${overage_count} overage @ $0.15 = $${overage_charge.toFixed(2)})`
            : ""}
        </span>
      </div>
      <div
        style={{
          height: 8,
          borderRadius: 4,
          background: "var(--border, #1f2937)",
          overflow: "hidden",
        }}
      >
        <div style={{ width: `${pct}%`, height: "100%", background: color }} />
      </div>
    </div>
  );
}

export default function QuoteRequests() {
  const { user, token } = useAuth();
  const tenantId = user?.tenantId;

  const [items, setItems] = useState([]);
  const [usage, setUsage] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [needsHumanOnly, setNeedsHumanOnly] = useState(false);
  const [modalImage, setModalImage] = useState(null);

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPhotoQuotes(tenantId, token, {
        needsHuman: needsHumanOnly ? true : undefined,
      });
      setItems(data.items || []);
      setUsage(data.usage || null);
      setTelemetry(data.telemetry || null);
    } catch (e) {
      setError(e?.message || "Failed to load quote requests.");
    } finally {
      setLoading(false);
    }
  }, [tenantId, token, needsHumanOnly]);

  const rate = async (quoteId, feedback) => {
    // Optimistic: mark the row locally, then persist.
    setItems((prev) =>
      prev.map((q) => (q.id === quoteId ? { ...q, tenant_feedback: feedback } : q)),
    );
    try {
      await submitQuoteFeedback(tenantId, token, quoteId, feedback);
    } catch (e) {
      // Non-fatal: reload to resync on failure.
      load();
    }
  };

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div style={{ padding: "24px 28px", maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem", color: "var(--text-primary)" }}>
          Quote Requests
        </h1>
        <p style={{ margin: "6px 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>
          Photo quotes from your widget, with this month&apos;s usage.
        </p>
      </div>

      <UsageMeter usage={usage} />

      {telemetry ? (
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <MetricCard
            label="Error rate (7d)"
            value={`${Math.round((telemetry.error_rate?.error_rate || 0) * 100)}%`}
            sub={`${telemetry.error_rate?.rated || 0} rated`}
            danger={telemetry.error_rate?.over_threshold}
          />
          <MetricCard
            label="Conversion (30d)"
            value={`${Math.round((telemetry.conversion?.conversion_rate || 0) * 100)}%`}
            sub={`${telemetry.conversion?.converted || 0} of ${telemetry.conversion?.total || 0}`}
          />
        </div>
      ) : null}

      <div style={{ display: "flex", gap: 14, marginBottom: 16, alignItems: "center" }}>
        <label style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
          <input
            type="checkbox"
            checked={needsHumanOnly}
            onChange={(e) => setNeedsHumanOnly(e.target.checked)}
            style={{ marginRight: 6 }}
          />
          Needs human only
        </label>
      </div>

      {loading && (
        <p style={{ color: "var(--text-muted)" }}>Loading quote requests…</p>
      )}

      {error && !loading && (
        <p style={{ color: "#ef4444" }}>{error}</p>
      )}

      {!loading && !error && items.length === 0 && (
        <div
          style={{
            border: "1px dashed var(--border, #1f2937)",
            borderRadius: 10,
            padding: 32,
            textAlign: "center",
            color: "var(--text-muted)",
          }}
        >
          <p style={{ margin: 0 }}>No photo quotes yet.</p>
          <p style={{ margin: "8px 0 0", fontSize: "0.85rem" }}>
            Enable photo-quote in your widget settings so visitors can upload a
            photo and get an instant estimate.
          </p>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ color: "var(--text-muted)", textAlign: "left" }}>
                <th style={{ padding: 8 }}>Date</th>
                <th style={{ padding: 8 }}>Photo</th>
                <th style={{ padding: 8 }}>Range</th>
                <th style={{ padding: 8 }}>Severity</th>
                <th style={{ padding: 8 }}>Confidence</th>
                <th style={{ padding: 8 }}>Outcome</th>
                <th style={{ padding: 8 }}>Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {items.map((q) => (
                <tr
                  key={q.id}
                  style={{ borderTop: "1px solid var(--border, #1f2937)", color: "var(--text-primary)" }}
                >
                  <td style={{ padding: 8, whiteSpace: "nowrap" }}>
                    {q.created_at ? q.created_at.slice(0, 10) : "-"}
                  </td>
                  <td style={{ padding: 8 }}>
                    {q.image_purged ? (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        image purged after 30d
                      </span>
                    ) : q.thumbnail_url ? (
                      <button
                        type="button"
                        onClick={() => setModalImage(q.image_url || q.thumbnail_url)}
                        style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
                        title="View full image"
                      >
                        <img
                          src={q.thumbnail_url}
                          alt="quote"
                          style={{ width: 48, height: 48, objectFit: "cover", borderRadius: 6 }}
                        />
                      </button>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td style={{ padding: 8 }}>
                    {q.needs_human
                      ? "-"
                      : `$${q.quote_low ?? 0}–$${q.quote_high ?? 0}`}
                  </td>
                  <td style={{ padding: 8 }}>{q.severity || "-"}</td>
                  <td style={{ padding: 8 }}>
                    {q.confidence != null ? `${Math.round(q.confidence * 100)}%` : "-"}
                  </td>
                  <td style={{ padding: 8 }}>
                    {q.needs_human ? (
                      <span style={{ color: "#f59e0b" }}>Needs human</span>
                    ) : (
                      <span style={{ color: "#22c55e" }}>Quoted</span>
                    )}
                  </td>
                  <td style={{ padding: 8, whiteSpace: "nowrap" }}>
                    {q.tenant_feedback ? (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        {q.tenant_feedback.replace("_", " ")}
                      </span>
                    ) : (
                      ["correct", "too_low", "too_high", "unclear"].map((f) => (
                        <button
                          key={f}
                          type="button"
                          onClick={() => rate(q.id, f)}
                          title={`Mark ${f.replace("_", " ")}`}
                          style={{
                            background: "none",
                            border: "1px solid var(--border, #1f2937)",
                            color: "var(--text-muted)",
                            borderRadius: 5,
                            cursor: "pointer",
                            fontSize: "0.7rem",
                            padding: "2px 5px",
                            marginRight: 3,
                          }}
                        >
                          {f === "correct"
                            ? "OK"
                            : f === "too_low"
                              ? "Low"
                              : f === "too_high"
                                ? "High"
                                : "?"}
                        </button>
                      ))
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modalImage && (
        <div
          onClick={() => setModalImage(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <img
            src={modalImage}
            alt="quote full"
            style={{ maxWidth: "90vw", maxHeight: "90vh", borderRadius: 8 }}
          />
        </div>
      )}
    </div>
  );
}
