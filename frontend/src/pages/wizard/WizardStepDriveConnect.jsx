// frontend/src/pages/wizard/WizardStepDriveConnect.jsx
//
// Final OPTIONAL wizard step (#53): connect a Google Drive folder so the
// widget learns the tenant's brand voice from their own docs. Genuinely
// skippable, no dark patterns. Consumes the live drive-KB backend
// (backend/routers/kb_integrations.py) via utils/api/tenant-kb.js.
//
// OAuth note: the backend /callback redirects to /dashboard/knowledge?drive=
// connected (not back here), so "Connect" hands off to Google and the tenant
// lands on the Knowledge page to finish. When the tenant is ALREADY connected
// (e.g. returned to the wizard), the folder picker runs inline and kicks off
// the first sync here.
import { useEffect, useState } from "react";

import { trackWizardEvent } from "../../utils/api/onboarding";
import {
  driveSyncNow,
  getDriveAuthUrl,
  getDriveStatus,
  listDriveFolders,
  setDriveFolder,
} from "../../utils/api/tenant-kb";

const STEP_INDEX = 7;

const box = {
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 14,
  padding: 24,
  marginBottom: 16,
};

const primaryBtn = {
  display: "block",
  width: "100%",
  padding: "14px",
  background: "#6366f1",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: "1rem",
  fontWeight: 700,
  cursor: "pointer",
};

const skipBtn = {
  display: "block",
  width: "100%",
  padding: "12px",
  marginTop: 12,
  background: "none",
  color: "rgba(255,255,255,0.55)",
  border: "none",
  fontSize: "0.9rem",
  cursor: "pointer",
};

export default function WizardStepDriveConnect({ token, tenantId, onDone, onSkip }) {
  const [phase, setPhase] = useState("loading"); // loading | intro | picker | unavailable | done
  const [folders, setFolders] = useState([]);
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [syncSummary, setSyncSummary] = useState(null);

  const track = (action) => {
    if (tenantId && token) trackWizardEvent(tenantId, token, STEP_INDEX, action);
  };

  // On entry: announce the step + read connection state to pick the branch.
  useEffect(() => {
    let cancelled = false;
    track("onboarding.drive_step_shown");
    (async () => {
      try {
        const st = await getDriveStatus(token);
        if (cancelled) return;
        setStatus(st);
        if (!st?.configured) {
          setPhase("unavailable");
        } else if (st?.connected) {
          loadFolders();
        } else {
          setPhase("intro");
        }
      } catch {
        // Treat any status failure as "not available yet" so the step stays
        // skippable and never blocks finishing onboarding.
        if (!cancelled) setPhase("unavailable");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tenantId]);

  const loadFolders = async () => {
    setPhase("picker");
    setError(null);
    try {
      const data = await listDriveFolders(token);
      const list = (data?.folders || []).map((f) => ({
        id: f.id || f.folder_id,
        name: f.name || f.folder_name || "Untitled folder",
      }));
      setFolders(list);
    } catch (e) {
      setError(e?.body?.detail || e?.message || "Could not list your Drive folders.");
    }
  };

  const connect = async () => {
    setBusy(true);
    setError(null);
    try {
      const { auth_url } = await getDriveAuthUrl(token);
      track("drive_connected");
      window.location.href = auth_url;
    } catch (e) {
      setBusy(false);
      setError(
        e?.body?.detail?.message ||
          e?.body?.detail ||
          e?.message ||
          "Google Drive sync isn't available right now.",
      );
    }
  };

  const chooseFolder = async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const res = await setDriveFolder(token, selected.id, selected.name);
      setSyncSummary(res?.sync || null);
      track("drive_initial_sync_complete");
      setPhase("done");
    } catch (e) {
      setError(e?.body?.detail || e?.message || "Could not start the sync.");
    } finally {
      setBusy(false);
    }
  };

  const resync = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await driveSyncNow(token);
      setSyncSummary(res?.sync || null);
      track("drive_initial_sync_complete");
      setPhase("done");
    } catch (e) {
      setError(e?.body?.detail || e?.message || "Could not start the sync.");
    } finally {
      setBusy(false);
    }
  };

  const skip = () => {
    track("drive_skipped");
    onSkip();
  };

  return (
    <div>
      <div style={{ textAlign: "center", marginBottom: 20 }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, margin: "0 0 8px" }}>
          Connect Google Drive (optional)
        </h2>
        <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "0.92rem", margin: 0 }}>
          Drop your brand docs in a shared Drive folder and your widget learns
          your voice in 5 minutes. Skip to upload manually later.
        </p>
      </div>

      {error && (
        <p style={{ color: "#f87171", fontSize: "0.85rem", textAlign: "center" }}>{error}</p>
      )}

      {phase === "loading" && (
        <p style={{ color: "rgba(255,255,255,0.45)", textAlign: "center" }}>Checking...</p>
      )}

      {phase === "intro" && (
        <div style={box}>
          <button type="button" style={primaryBtn} onClick={connect} disabled={busy}>
            {busy ? "Opening Google..." : "Connect Google Drive"}
          </button>
          <button type="button" style={skipBtn} onClick={skip}>
            Skip for now
          </button>
        </div>
      )}

      {phase === "unavailable" && (
        <div style={box}>
          <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.9rem", marginTop: 0 }}>
            Google Drive sync isn&apos;t available on your workspace yet. You can
            upload brand docs anytime from Knowledge in the dashboard.
          </p>
          <button type="button" style={primaryBtn} onClick={onDone}>
            Finish
          </button>
        </div>
      )}

      {phase === "picker" && (
        <div style={box}>
          {status?.folder_id ? (
            <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.88rem", marginTop: 0 }}>
              Currently syncing <strong>{status.folder_name}</strong>. Pick a
              different folder below or re-run the sync.
            </p>
          ) : (
            <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.88rem", marginTop: 0 }}>
              Choose the folder your widget should learn from.
            </p>
          )}

          {folders.length === 0 ? (
            <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.85rem" }}>
              No shared folders found in this Drive account.
            </p>
          ) : (
            <div style={{ maxHeight: 220, overflowY: "auto", margin: "8px 0 16px" }}>
              {folders.map((f) => (
                <label
                  key={f.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "9px 6px",
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    cursor: "pointer",
                    color: "rgba(255,255,255,0.85)",
                    fontSize: "0.9rem",
                  }}
                >
                  <input
                    type="radio"
                    name="drive-folder"
                    checked={selected?.id === f.id}
                    onChange={() => setSelected(f)}
                  />
                  {f.name}
                </label>
              ))}
            </div>
          )}

          <button
            type="button"
            style={{ ...primaryBtn, opacity: selected ? 1 : 0.5 }}
            onClick={chooseFolder}
            disabled={!selected || busy}
          >
            {busy ? "Syncing..." : "Use this folder and sync"}
          </button>
          {status?.folder_id && (
            <button
              type="button"
              style={{ ...skipBtn, color: "#a5b4fc" }}
              onClick={resync}
              disabled={busy}
            >
              Re-sync current folder
            </button>
          )}
          <button type="button" style={skipBtn} onClick={skip}>
            Skip for now
          </button>
        </div>
      )}

      {phase === "done" && (
        <div style={box}>
          <div
            style={{
              background: "rgba(134,239,172,0.1)",
              border: "1px solid rgba(134,239,172,0.3)",
              borderRadius: 12,
              padding: "18px 16px",
              marginBottom: 16,
              textAlign: "center",
            }}
          >
            <div style={{ color: "#86efac", fontWeight: 700, marginBottom: 4 }}>
              Drive connected
            </div>
            <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "0.85rem", margin: 0 }}>
              {syncSummary
                ? `Synced ${syncSummary.files_added ?? 0} added, ${
                    syncSummary.files_updated ?? 0
                  } updated. Your widget is learning your brand voice now.`
                : "Your widget is learning your brand voice now."}
            </p>
          </div>
          <button type="button" style={primaryBtn} onClick={onDone}>
            Finish
          </button>
        </div>
      )}
    </div>
  );
}
