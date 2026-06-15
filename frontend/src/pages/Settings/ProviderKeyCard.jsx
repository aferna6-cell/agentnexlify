import { useState } from "react";

const HEALTH_PILL = {
  green: { bg: "#14532d", color: "#4ade80", label: "Healthy" },
  yellow: { bg: "#713f12", color: "#fbbf24", label: "Warning" },
  red: { bg: "#7f1d1d", color: "#f87171", label: "Error" },
};

function HealthPill({ health, detail }) {
  const pill = HEALTH_PILL[health] || HEALTH_PILL.yellow;
  return (
    <span
      title={detail || ""}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        padding: "2px 10px",
        borderRadius: "12px",
        fontSize: "0.75rem",
        fontWeight: 600,
        background: pill.bg,
        color: pill.color,
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          background: pill.color,
          flexShrink: 0,
        }}
      />
      {pill.label}
    </span>
  );
}

/**
 * Renders a single integration provider's key card.
 *
 * Props:
 *   provider      – string key ("stripe" | "twilio" | "resend")
 *   label         – display name
 *   data          – { masked_key, health, detail, last_verified_at } or null when not configured
 *   onSave(provider, plaintext)  – async fn
 *   onVerify(provider)           – async fn, returns { health, detail }
 *   onRemove(provider)           – async fn, throws ApiError(409) if Stripe active
 */
export default function ProviderKeyCard({
  provider,
  label,
  data,
  onSave,
  onVerify,
  onRemove,
}) {
  const [editing, setEditing] = useState(false);
  const [inputVal, setInputVal] = useState("");
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [liveHealth, setLiveHealth] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const [saveError, setSaveError] = useState(null);

  const health = liveHealth?.health ?? data?.health ?? null;
  const detail = liveHealth?.detail ?? data?.detail ?? null;

  const handleSave = async () => {
    if (!inputVal.trim()) return;
    setSaving(true);
    setSaveError(null);
    try {
      const result = await onSave(provider, inputVal.trim());
      setLiveHealth(result ? { health: result.verified ? "green" : "yellow", detail: "" } : null);
      setEditing(false);
      setInputVal("");
    } catch (err) {
      setSaveError(err?.body?.detail || err?.message || "Failed to save key");
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const result = await onVerify(provider);
      if (result) setLiveHealth(result);
    } catch (err) {
      setLiveHealth({ health: "red", detail: err?.body?.detail || err?.message || "Verification failed" });
    } finally {
      setVerifying(false);
    }
  };

  const handleRemove = async () => {
    setDeleteError(null);
    setRemoving(true);
    try {
      await onRemove(provider);
      setLiveHealth(null);
    } catch (err) {
      if (err?.status === 409) {
        setDeleteError(
          "Cannot remove - active Stripe subscription. Cancel/migrate the subscription first."
        );
      } else {
        setDeleteError(err?.body?.detail || err?.message || "Failed to remove key");
      }
    } finally {
      setRemoving(false);
    }
  };

  const configured = !!data?.masked_key;

  return (
    <div
      style={{
        background: "#0f0f17",
        border: "1px solid #1f1f2e",
        borderRadius: "10px",
        padding: "20px 24px",
        marginBottom: "16px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "6px",
            }}
          >
            <span
              style={{
                fontWeight: 600,
                fontSize: "0.95rem",
                color: "var(--text-primary, #f1f5f9)",
              }}
            >
              {label}
            </span>
            {configured && health && (
              <HealthPill health={health} detail={detail} />
            )}
            {!configured && (
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-muted, #6b7280)",
                  padding: "2px 8px",
                  background: "#1c1c2e",
                  borderRadius: "10px",
                }}
              >
                Not configured
              </span>
            )}
          </div>

          {configured && (
            <div
              style={{
                fontSize: "0.82rem",
                color: "var(--text-secondary, #94a3b8)",
                fontFamily: "monospace",
                marginBottom: detail ? "4px" : 0,
              }}
            >
              {data.masked_key}
            </div>
          )}

          {detail && (
            <div
              style={{
                fontSize: "0.78rem",
                color: "var(--text-muted, #6b7280)",
                marginTop: "2px",
              }}
            >
              {detail}
            </div>
          )}

          {data?.last_verified_at && (
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted, #6b7280)",
                marginTop: "4px",
              }}
            >
              Last verified{" "}
              {new Date(data.last_verified_at).toLocaleDateString(undefined, {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            </div>
          )}
        </div>

        <div
          style={{
            display: "flex",
            gap: "8px",
            flexShrink: 0,
            alignItems: "center",
          }}
        >
          {configured && !editing && (
            <>
              <button
                className="btn-secondary"
                style={{ fontSize: "0.8rem", padding: "5px 12px" }}
                onClick={handleVerify}
                disabled={verifying}
              >
                {verifying ? "Verifying..." : "Verify"}
              </button>
              <button
                className="btn-secondary"
                style={{ fontSize: "0.8rem", padding: "5px 12px" }}
                onClick={() => {
                  setEditing(true);
                  setSaveError(null);
                  setDeleteError(null);
                }}
              >
                Edit key
              </button>
              <button
                className="btn-danger"
                style={{ fontSize: "0.8rem", padding: "5px 12px" }}
                onClick={handleRemove}
                disabled={removing}
              >
                {removing ? "Removing..." : "Remove"}
              </button>
            </>
          )}

          {!configured && !editing && (
            <button
              className="btn-primary"
              style={{ fontSize: "0.8rem", padding: "5px 14px" }}
              onClick={() => {
                setEditing(true);
                setSaveError(null);
              }}
            >
              Add key
            </button>
          )}
        </div>
      </div>

      {editing && (
        <div style={{ marginTop: "16px" }}>
          <div
            style={{
              display: "flex",
              gap: "8px",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <input
              type="password"
              autoComplete="off"
              placeholder={`Paste your ${label} secret key`}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              style={{
                flex: 1,
                minWidth: "200px",
                background: "#1c1c2e",
                border: "1px solid #2e2e4e",
                borderRadius: "6px",
                color: "var(--text-primary, #f1f5f9)",
                padding: "7px 12px",
                fontSize: "0.85rem",
                outline: "none",
              }}
            />
            <button
              className="btn-primary"
              style={{ fontSize: "0.8rem", padding: "7px 16px" }}
              onClick={handleSave}
              disabled={saving || !inputVal.trim()}
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              className="btn-secondary"
              style={{ fontSize: "0.8rem", padding: "7px 12px" }}
              onClick={() => {
                setEditing(false);
                setInputVal("");
                setSaveError(null);
              }}
            >
              Cancel
            </button>
          </div>
          {saveError && (
            <p
              style={{
                marginTop: "8px",
                fontSize: "0.8rem",
                color: "#f87171",
              }}
            >
              {saveError}
            </p>
          )}
        </div>
      )}

      {deleteError && (
        <p
          style={{
            marginTop: "10px",
            fontSize: "0.82rem",
            color: "#fbbf24",
            background: "#1c1200",
            border: "1px solid #713f12",
            borderRadius: "6px",
            padding: "8px 12px",
          }}
        >
          {deleteError}
        </p>
      )}
    </div>
  );
}
