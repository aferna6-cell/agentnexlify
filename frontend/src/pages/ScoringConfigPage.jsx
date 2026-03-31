import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchScoringFactors, updateScoringFactor,
  createScoringFactor, deleteScoringFactor, resetScoringFactors,
} from "../utils/api/scoring";

export default function ScoringConfigPage() {
  const { user, token } = useAuth();
  const tenantId = user?.tenant_id;

  const [factors, setFactors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionMsg, setActionMsg] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newFactor, setNewFactor] = useState({ factor: "", weight: 10, description: "" });

  const load = useCallback(async () => {
    if (!tenantId) return;
    try {
      const res = await fetchScoringFactors(tenantId, token);
      setFactors(res.factors || []);
      setError(null);
    } catch (e) {
      setError(e.message || "Failed to load scoring config");
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => { load(); }, [load]);

  const flash = (msg) => { setActionMsg(msg); setTimeout(() => setActionMsg(null), 3000); };

  const handleWeightChange = async (factorId, weight) => {
    const f = factors.find(x => x.id === factorId);
    if (!f) return;
    try {
      await updateScoringFactor(tenantId, factorId, { weight: parseInt(weight), is_enabled: f.is_enabled }, token);
      setFactors(prev => prev.map(x => x.id === factorId ? { ...x, weight: parseInt(weight) } : x));
    } catch (e) {
      flash(`Error: ${e.message}`);
    }
  };

  const handleToggle = async (factorId) => {
    const f = factors.find(x => x.id === factorId);
    if (!f) return;
    try {
      await updateScoringFactor(tenantId, factorId, { weight: f.weight, is_enabled: !f.is_enabled }, token);
      setFactors(prev => prev.map(x => x.id === factorId ? { ...x, is_enabled: !x.is_enabled } : x));
    } catch (e) {
      flash(`Error: ${e.message}`);
    }
  };

  const handleAdd = async () => {
    if (!newFactor.factor.trim()) return;
    try {
      await createScoringFactor(tenantId, {
        factor: newFactor.factor.trim(),
        weight: parseInt(newFactor.weight) || 10,
        description: newFactor.description || null,
      }, token);
      setShowAdd(false);
      setNewFactor({ factor: "", weight: 10, description: "" });
      flash("Factor added");
      load();
    } catch (e) {
      flash(`Error: ${e.message}`);
    }
  };

  const handleDelete = async (factorId) => {
    if (!confirm("Delete this scoring factor?")) return;
    try {
      await deleteScoringFactor(tenantId, factorId, token);
      flash("Factor deleted");
      load();
    } catch (e) {
      flash(`Error: ${e.message}`);
    }
  };

  const handleReset = async () => {
    if (!confirm("Reset all scoring factors to defaults? This will delete any custom factors.")) return;
    try {
      await resetScoringFactors(tenantId, token);
      flash("Reset to defaults");
      load();
    } catch (e) {
      flash(`Error: ${e.message}`);
    }
  };

  if (loading) return <SkeletonLoader />;

  const totalWeight = factors.filter(f => f.is_enabled).reduce((sum, f) => sum + f.weight, 0);

  return (
    <div style={{ padding: "28px 32px", maxWidth: 900 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            Lead Scoring Configuration
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: "4px 0 0", fontSize: 14 }}>
            Customize how leads are scored based on conversation signals
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => setShowAdd(true)} style={{
            padding: "8px 16px", borderRadius: 8, border: "none",
            background: "var(--accent)", color: "#fff", cursor: "pointer", fontWeight: 600, fontSize: 13,
          }}>
            + Add Factor
          </button>
          <button onClick={handleReset} style={{
            padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)",
            background: "transparent", color: "var(--text-secondary)", cursor: "pointer", fontSize: 13,
          }}>
            Reset Defaults
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "rgba(239,68,68,0.1)", borderRadius: 8, marginBottom: 16, color: "#ef4444" }}>
          {error}
        </div>
      )}
      {actionMsg && (
        <div style={{ padding: "12px 16px", background: "rgba(34,197,94,0.1)", borderRadius: 8, marginBottom: 16, color: "#22c55e" }}>
          {actionMsg}
        </div>
      )}

      {/* Weight total indicator */}
      <div style={{
        background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 10,
        padding: "14px 20px", marginBottom: 20, display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <span style={{ color: "var(--text-secondary)", fontSize: 14 }}>
          Total weight of enabled factors:
        </span>
        <span style={{ color: totalWeight === 100 ? "#22c55e" : "#f59e0b", fontWeight: 700, fontSize: 18 }}>
          {totalWeight}
          <span style={{ fontSize: 12, fontWeight: 400, marginLeft: 4 }}>/ 100 recommended</span>
        </span>
      </div>

      {/* Factors list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {factors.map(f => (
          <div key={f.id} style={{
            background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 10,
            padding: "16px 20px", opacity: f.is_enabled ? 1 : 0.5,
            display: "flex", alignItems: "center", gap: 16,
          }}>
            {/* Toggle */}
            <button onClick={() => handleToggle(f.id)} style={{
              width: 36, height: 20, borderRadius: 10, border: "none", cursor: "pointer",
              background: f.is_enabled ? "var(--accent)" : "var(--border)",
              position: "relative", flexShrink: 0,
            }}>
              <div style={{
                width: 16, height: 16, borderRadius: "50%", background: "#fff",
                position: "absolute", top: 2,
                left: f.is_enabled ? 18 : 2, transition: "left 0.2s",
              }} />
            </button>

            {/* Info */}
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15, textTransform: "capitalize" }}>
                {f.factor.replace(/_/g, " ")}
              </div>
              {f.description && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>{f.description}</div>
              )}
            </div>

            {/* Weight slider */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
              <input
                type="range"
                min={0}
                max={100}
                value={f.weight}
                onChange={e => setFactors(prev => prev.map(x => x.id === f.id ? { ...x, weight: parseInt(e.target.value) } : x))}
                onMouseUp={e => handleWeightChange(f.id, e.target.value)}
                onTouchEnd={e => handleWeightChange(f.id, e.target.value)}
                style={{ width: 120, accentColor: "var(--accent)" }}
              />
              <span style={{ fontWeight: 700, color: "var(--accent)", fontSize: 16, width: 36, textAlign: "right" }}>
                {f.weight}
              </span>
            </div>

            {/* Delete */}
            <button onClick={() => handleDelete(f.id)} style={{
              padding: "4px 8px", borderRadius: 4, border: "1px solid var(--border)",
              background: "transparent", color: "#ef4444", cursor: "pointer", fontSize: 12,
            }}>
              Del
            </button>
          </div>
        ))}
      </div>

      {factors.length === 0 && (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-secondary)" }}>
          <h3 style={{ color: "var(--text-primary)", marginBottom: 8 }}>No scoring factors</h3>
          <p>Click "Add Factor" or "Reset Defaults" to get started.</p>
        </div>
      )}

      {/* Add factor modal */}
      {showAdd && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
        }} onClick={() => setShowAdd(false)}>
          <div style={{
            background: "var(--card-bg)", borderRadius: 12, padding: 24, maxWidth: 420, width: "90%",
            border: "1px solid var(--border)",
          }} onClick={e => e.stopPropagation()}>
            <h3 style={{ color: "var(--text-primary)", marginBottom: 16 }}>Add Custom Scoring Factor</h3>

            <label style={{ fontSize: 13, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Factor Name</label>
            <input
              value={newFactor.factor}
              onChange={e => setNewFactor({ ...newFactor, factor: e.target.value })}
              placeholder="e.g. referral_source"
              style={{
                width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)",
                background: "var(--input-bg)", color: "var(--text-primary)", marginBottom: 12, fontSize: 14,
              }}
            />

            <label style={{ fontSize: 13, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Description</label>
            <input
              value={newFactor.description}
              onChange={e => setNewFactor({ ...newFactor, description: e.target.value })}
              placeholder="Explains what this factor measures"
              style={{
                width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)",
                background: "var(--input-bg)", color: "var(--text-primary)", marginBottom: 12, fontSize: 14,
              }}
            />

            <label style={{ fontSize: 13, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>Weight (0-100)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={newFactor.weight}
              onChange={e => setNewFactor({ ...newFactor, weight: e.target.value })}
              style={{
                width: 100, padding: 10, borderRadius: 6, border: "1px solid var(--border)",
                background: "var(--input-bg)", color: "var(--text-primary)", marginBottom: 16, fontSize: 14,
              }}
            />

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setShowAdd(false)} style={{
                padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)",
                background: "transparent", color: "var(--text-secondary)", cursor: "pointer",
              }}>Cancel</button>
              <button onClick={handleAdd} style={{
                padding: "8px 16px", borderRadius: 6, border: "none",
                background: "var(--accent)", color: "#fff", cursor: "pointer", fontWeight: 600,
              }}>Add Factor</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
