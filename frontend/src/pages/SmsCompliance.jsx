import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { request } from "../utils/api/_client";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: "16px 20px",
};

const btnStyle = {
  border: "none",
  borderRadius: 6,
  padding: "8px 16px",
  cursor: "pointer",
  fontSize: "0.85rem",
  color: "#fff",
};

export default function SmsCompliance() {
  const { token } = useAuth();
  const [stats, setStats] = useState(null);
  const [optOuts, setOptOuts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [manualPhone, setManualPhone] = useState("");
  const [actionMsg, setActionMsg] = useState(null);

  const PER_PAGE = 50;

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [statsData, listData] = await Promise.all([
        request("/api/v1/sms-compliance/stats", { token }),
        request(`/api/v1/sms-compliance/opt-outs?page=${page}&per_page=${PER_PAGE}`, { token }),
      ]);
      setStats(statsData);
      setOptOuts(listData.items || []);
      setTotal(listData.total || 0);
    } catch (e) {
      setError(e.message || "Failed to load compliance data");
    } finally {
      setLoading(false);
    }
  }, [token, page]);

  useEffect(() => {
    load();
  }, [load]);

  async function submitManual(path, label) {
    if (!manualPhone.trim()) return;
    try {
      await request(`/api/v1/sms-compliance/${path}`, {
        method: "POST",
        token,
        body: { phone: manualPhone.trim() },
      });
      setActionMsg(`${label} recorded for ${manualPhone.trim()}`);
      setManualPhone("");
      load();
    } catch (e) {
      setActionMsg(`Error: ${e.message}`);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));

  return (
    <div style={{ padding: "24px 28px", maxWidth: 900, color: "var(--text-primary)" }}>
      <h1 style={{ margin: 0, fontSize: "1.5rem" }}>SMS Compliance</h1>
      <p style={{ color: "var(--text-muted)", margin: "6px 0 24px", fontSize: "0.9rem" }}>
        TCPA opt-out ledger. Every number here is suppressed from all outbound SMS.
      </p>

      {stats && (
        <div style={{ ...cardStyle, display: "inline-block", marginBottom: 24 }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{stats.total_opt_outs}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Total opt-outs</div>
        </div>
      )}

      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3 style={{ marginTop: 0, marginBottom: 12, fontSize: "1rem" }}>Manual override</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input
            type="tel"
            placeholder="Phone number"
            value={manualPhone}
            onChange={(e) => setManualPhone(e.target.value)}
            style={{
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "8px 12px",
              color: "var(--text-primary)",
              width: 200,
            }}
          />
          <button
            onClick={() => submitManual("opt-out", "Opt-out")}
            style={{ ...btnStyle, background: "var(--danger, #c0392b)" }}
          >
            Record opt-out
          </button>
          <button
            onClick={() => submitManual("opt-in", "Opt-in (opt-out removed)")}
            style={{ ...btnStyle, background: "var(--accent, #6366f1)" }}
          >
            Remove opt-out
          </button>
        </div>
        {actionMsg && (
          <div style={{ marginTop: 8, fontSize: 13, color: "var(--text-muted)" }}>{actionMsg}</div>
        )}
      </div>

      {loading && <p style={{ color: "var(--text-muted)" }}>Loading…</p>}
      {error && <p style={{ color: "var(--danger, #c0392b)" }}>{error}</p>}

      {!loading && !error && (
        <>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr
                  style={{
                    borderBottom: "1px solid var(--border)",
                    color: "var(--text-muted)",
                  }}
                >
                  <th style={{ textAlign: "left", padding: "8px 12px" }}>Phone</th>
                  <th style={{ textAlign: "left", padding: "8px 12px" }}>Source</th>
                  <th style={{ textAlign: "left", padding: "8px 12px" }}>Recorded</th>
                </tr>
              </thead>
              <tbody>
                {optOuts.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ padding: "24px 12px", color: "var(--text-muted)" }}>
                      No opt-outs recorded. Contacts who reply STOP will appear here
                      automatically.
                    </td>
                  </tr>
                ) : (
                  optOuts.map((row) => (
                    <tr key={row.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 12px", fontFamily: "monospace" }}>
                        {row.phone_masked}
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>
                        {row.source || "—"}
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>
                        {row.created_at ? new Date(row.created_at).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div style={{ display: "flex", gap: 8, marginTop: 16, alignItems: "center" }}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{
                  padding: "6px 12px",
                  background: "var(--bg-secondary, var(--card-bg))",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  color: "var(--text-primary)",
                  cursor: page === 1 ? "default" : "pointer",
                  opacity: page === 1 ? 0.4 : 1,
                }}
              >
                Prev
              </button>
              <span style={{ color: "var(--text-muted)", fontSize: 13 }}>
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                style={{
                  padding: "6px 12px",
                  background: "var(--bg-secondary, var(--card-bg))",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  color: "var(--text-primary)",
                  cursor: page === totalPages ? "default" : "pointer",
                  opacity: page === totalPages ? 0.4 : 1,
                }}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
