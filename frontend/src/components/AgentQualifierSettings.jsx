import { useEffect, useState } from "react";
import { fetchQualifierSettings, updateQualifierSettings } from "../utils/api/qualifier";

/**
 * Owner controls for the AI lead qualifier (migration 147).
 *
 * - qualifier_enabled: kill switch to pause AI qualification without
 *   dropping the plan.
 * - qualifier_min_intent: only spend on the AI qualifier when the cheap
 *   rule-based lead score (0-10) clears this threshold. 0 = always.
 *
 * Self-contained: loads + saves its own state so it can mount into the
 * Settings page without bloating that page's god-class render.
 */
export default function AgentQualifierSettings({ tenantId, token }) {
  const [enabled, setEnabled] = useState(true);
  const [minIntent, setMinIntent] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!tenantId || !token) return undefined;
    let active = true;
    setLoading(true);
    setError(null);
    fetchQualifierSettings(tenantId, token)
      .then((data) => {
        if (!active) return;
        setEnabled(data.qualifier_enabled !== false);
        setMinIntent(Number(data.qualifier_min_intent) || 0);
      })
      .catch(() => {
        if (active) setError("Could not load qualifier settings.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [tenantId, token]);

  async function handleSave() {
    setSaving(true);
    setStatus(null);
    setError(null);
    try {
      await updateQualifierSettings(
        tenantId,
        { qualifier_enabled: enabled, qualifier_min_intent: minIntent },
        token,
      );
      setStatus("Saved");
    } catch (err) {
      setError(
        err?.status === 503
          ? "Qualifier settings aren't available yet. Try again shortly."
          : "Could not save. Check your connection and try again.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="agent-control-card qualifier-settings">
      <style>{`
        .qualifier-settings { padding: 24px; }
        .qualifier-settings .qs-head { margin-bottom: 4px; }
        .qualifier-settings h2 {
          margin: 0; font-size: 16px; font-weight: 600; color: var(--text-primary);
        }
        .qualifier-settings .qs-sub {
          margin: 6px 0 20px; font-size: 13px; color: var(--text-secondary);
          max-width: 640px; line-height: 1.5;
        }
        .qualifier-settings .qs-row {
          display: flex; align-items: flex-start; justify-content: space-between;
          gap: 24px; padding: 16px 0; border-top: 1px solid var(--border);
        }
        .qualifier-settings .qs-row-label { font-size: 14px; color: var(--text-primary); font-weight: 500; }
        .qualifier-settings .qs-row-help {
          margin-top: 4px; font-size: 12px; color: var(--text-muted);
          max-width: 460px; line-height: 1.5;
        }
        .qualifier-settings .qs-toggle {
          position: relative; width: 44px; height: 24px; border-radius: 999px;
          border: 1px solid var(--border); cursor: pointer; flex-shrink: 0;
          transition: background 0.15s ease;
        }
        .qualifier-settings .qs-toggle[data-on="true"] { background: var(--accent); border-color: var(--accent); }
        .qualifier-settings .qs-toggle[data-on="false"] { background: var(--bg-card); }
        .qualifier-settings .qs-knob {
          position: absolute; top: 2px; left: 2px; width: 18px; height: 18px;
          border-radius: 50%; background: var(--text-primary); transition: transform 0.15s ease;
        }
        .qualifier-settings .qs-toggle[data-on="true"] .qs-knob { transform: translateX(20px); background: #fff; }
        .qualifier-settings .qs-threshold { display: flex; align-items: center; gap: 14px; flex-shrink: 0; }
        .qualifier-settings .qs-threshold input[type="range"] { width: 180px; accent-color: var(--accent); }
        .qualifier-settings .qs-threshold-value {
          min-width: 56px; text-align: center; font-size: 13px; font-weight: 600;
          color: var(--text-primary); padding: 4px 8px; border: 1px solid var(--border);
          border-radius: 6px; background: var(--bg-card);
        }
        .qualifier-settings .qs-footer {
          display: flex; align-items: center; gap: 16px; margin-top: 20px;
          padding-top: 16px; border-top: 1px solid var(--border);
        }
        .qualifier-settings .qs-save {
          padding: 8px 18px; border-radius: 8px; border: none; cursor: pointer;
          background: var(--accent); color: #fff; font-size: 13px; font-weight: 600;
        }
        .qualifier-settings .qs-save:disabled { opacity: 0.5; cursor: default; }
        .qualifier-settings .qs-msg { font-size: 13px; }
        .qualifier-settings .qs-msg.ok { color: var(--green); }
        .qualifier-settings .qs-msg.err { color: var(--red); }
      `}</style>

      <div className="qs-head">
        <h2>AI Lead Qualifier</h2>
      </div>
      <p className="qs-sub">
        Controls whether new leads are scored by the AI qualifier and how selective it
        is. Reasoning for each qualified lead shows on the lead record and in QA
        scorecards above.
      </p>

      {loading ? (
        <p className="qs-row-help">Loading settings...</p>
      ) : (
        <>
          <div className="qs-row">
            <div>
              <div className="qs-row-label">Run AI qualification</div>
              <div className="qs-row-help">
                When off, new leads are still captured and rule-scored, but the AI
                qualifier does not run. No Managed-Agent cost while paused.
              </div>
            </div>
            <button
              type="button"
              className="qs-toggle"
              data-on={enabled ? "true" : "false"}
              role="switch"
              aria-checked={enabled}
              aria-label="Run AI qualification"
              onClick={() => setEnabled((v) => !v)}
            >
              <span className="qs-knob" />
            </button>
          </div>

          <div className="qs-row">
            <div>
              <div className="qs-row-label">Minimum lead score to qualify</div>
              <div className="qs-row-help">
                Only run the AI qualifier when the instant rule-based score (0-10)
                reaches this number. Higher means fewer, more promising leads get
                AI qualification. 0 runs it on every eligible lead.
              </div>
            </div>
            <div className="qs-threshold">
              <input
                type="range"
                min="0"
                max="10"
                step="1"
                value={minIntent}
                disabled={!enabled}
                onChange={(e) => setMinIntent(Number(e.target.value))}
                aria-label="Minimum lead score to qualify"
              />
              <span className="qs-threshold-value">
                {minIntent === 0 ? "All" : minIntent}
              </span>
            </div>
          </div>

          <div className="qs-footer">
            <button
              type="button"
              className="qs-save"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save changes"}
            </button>
            {status && <span className="qs-msg ok">{status}</span>}
            {error && <span className="qs-msg err">{error}</span>}
          </div>
        </>
      )}
    </section>
  );
}
