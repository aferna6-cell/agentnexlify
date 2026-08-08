import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  addKbNote,
  createKbSyncToken,
  deleteKbDocument,
  disconnectDrive,
  driveSyncNow,
  getDriveAuthUrl,
  getDriveStatus,
  getDriveSyncLog,
  listDriveFolders,
  listKbDocuments,
  setDriveFolder,
  uploadKbDocuments,
} from "../utils/api/tenant-kb";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: "18px 22px",
};

const btnStyle = {
  border: "none",
  borderRadius: 8,
  padding: "8px 16px",
  cursor: "pointer",
  fontSize: "0.85rem",
  color: "#fff",
  background: "var(--accent, #6366f1)",
};

const btnQuiet = {
  ...btnStyle,
  background: "var(--bg-primary)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
};

const SOURCE_LABELS = {
  upload: "Uploaded",
  drive: "Google Drive",
  local_sync: "Local sync",
  note: "Typed note",
};

function formatDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function KnowledgeSourcesPage() {
  const { user, token } = useAuth();
  const tenantId = user?.tenantId;

  const [docs, setDocs] = useState([]);
  const [docLimit, setDocLimit] = useState(0);
  const [drive, setDrive] = useState(null);
  const [folders, setFolders] = useState(null); // null = picker closed
  const [syncLog, setSyncLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [syncCmd, setSyncCmd] = useState(null);
  const [copied, setCopied] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const fileInputRef = useRef(null);

  // Spec Resolved-Q7-D: while a Drive folder is actively syncing, the KB
  // dashboard is read-only. Manual uploads/removals would be overwritten by
  // the next sync, so edit controls are disabled until sync is disconnected.
  const syncActive = Boolean(drive?.folder_id);

  const load = useCallback(async () => {
    if (!tenantId || !token) return;
    setLoading(true);
    try {
      const [docsRes, driveRes, logRes] = await Promise.allSettled([
        listKbDocuments(tenantId, token),
        getDriveStatus(token),
        getDriveSyncLog(token),
      ]);
      if (docsRes.status === "fulfilled") {
        setDocs(docsRes.value.documents || []);
        setDocLimit(docsRes.value.limit || 0);
      }
      if (driveRes.status === "fulfilled") setDrive(driveRes.value);
      if (logRes.status === "fulfilled") setSyncLog(logRes.value.log || []);
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []).filter((f) =>
      /\.(pdf|docx|txt|md|markdown)$/i.test(f.name),
    );
    if (!files.length) {
      setMessage("No supported files found (PDF, DOCX, TXT, MD).");
      return;
    }
    setBusy(true);
    setMessage(`Uploading ${files.length} file${files.length === 1 ? "" : "s"}…`);
    try {
      const res = await uploadKbDocuments(tenantId, token, files);
      const added = res.results.filter((r) => r.status === "added").length;
      const updated = res.results.filter((r) => r.status === "updated").length;
      const skipped = res.results.filter((r) => r.status === "skipped");
      let note = `${added} added, ${updated} updated`;
      if (skipped.length) note += `, ${skipped.length} skipped (${skipped[0].reason})`;
      setMessage(`${note}. Knowledge compiled - your AI answers from it now.`);
      load();
    } catch (e) {
      setMessage(e.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveNote() {
    const title = noteTitle.trim();
    const content = noteContent.trim();
    if (!title || !content) {
      setMessage("A note needs both a title and some text.");
      return;
    }
    setBusy(true);
    try {
      const res = await addKbNote(tenantId, token, title, content);
      setMessage(
        res.status === "updated"
          ? `Updated "${title}". Knowledge compiled - your AI answers from it now.`
          : `Saved "${title}". Knowledge compiled - your AI answers from it now.`,
      );
      setNoteTitle("");
      setNoteContent("");
      load();
    } catch (e) {
      const detail = e.body?.detail;
      setMessage(
        (typeof detail === "string" && detail) || e.message || "Could not save the note",
      );
    } finally {
      setBusy(false);
    }
  }

  async function connectDrive() {
    try {
      const { auth_url } = await getDriveAuthUrl(token);
      window.location.href = auth_url;
    } catch (e) {
      const detail = e.body?.detail;
      setMessage(detail?.message || e.message || "Drive connection unavailable");
    }
  }

  async function openFolderPicker() {
    setBusy(true);
    try {
      const res = await listDriveFolders(token);
      setFolders(res.folders || []);
    } catch (e) {
      setMessage(e.message || "Could not list Drive folders");
    } finally {
      setBusy(false);
    }
  }

  async function pickFolder(folder) {
    setBusy(true);
    setFolders(null);
    setMessage(`Syncing "${folder.name}"…`);
    try {
      const res = await setDriveFolder(token, folder.id, folder.name);
      const s = res.sync || {};
      setMessage(
        `Folder connected. First sync: ${s.added || 0} added, ${s.skipped || 0} skipped.`,
      );
      load();
    } catch (e) {
      setMessage(e.message || "Folder selection failed");
    } finally {
      setBusy(false);
    }
  }

  async function syncNow() {
    setBusy(true);
    setMessage("Syncing from Drive…");
    try {
      const res = await driveSyncNow(token);
      const s = res.sync || {};
      setMessage(
        s.error
          ? `Sync problem: ${s.error}`
          : `Synced: ${s.added || 0} added, ${s.updated || 0} updated, ${s.skipped || 0} skipped.`,
      );
      load();
    } catch (e) {
      setMessage(e.message || "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDisconnect() {
    setConfirmDisconnect(false);
    setBusy(true);
    try {
      await disconnectDrive(token);
      setMessage("Drive disconnected. Synced documents were kept.");
      load();
    } catch (e) {
      setMessage(e.message || "Disconnect failed");
    } finally {
      setBusy(false);
    }
  }

  async function generateSyncCommand() {
    setBusy(true);
    try {
      const res = await createKbSyncToken(tenantId, token);
      setSyncCmd(
        `python anx_kb_sync.py YOUR_FOLDER --tenant-id ${res.tenant_id} --token "${res.token}" --watch`,
      );
      setCopied(false);
    } catch (e) {
      setMessage(e.message || "Could not create a sync token");
    } finally {
      setBusy(false);
    }
  }

  async function copySyncCommand() {
    try {
      await navigator.clipboard.writeText(syncCmd);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  async function removeDoc(doc) {
    setBusy(true);
    try {
      await deleteKbDocument(tenantId, doc.id, token);
      setMessage(`Removed ${doc.filename} and recompiled.`);
      load();
    } catch (e) {
      setMessage(e.message || "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ padding: "24px 28px", maxWidth: 1000, color: "var(--text-primary)" }}>
      <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Knowledge</h1>
      <p style={{ color: "var(--text-muted)", margin: "6px 0 24px", fontSize: "0.9rem" }}>
        Your business&apos;s second brain. Every document here powers your AI&apos;s chat and
        phone answers, with full traceability back to the source file.
      </p>

      {message && (
        <div
          style={{
            ...cardStyle,
            marginBottom: 16,
            padding: "10px 16px",
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
          }}
        >
          {message}
        </div>
      )}

      {/* Read-only banner while Drive sync owns the KB (spec Resolved-Q7-D) */}
      {syncActive && (
        <div
          style={{
            ...cardStyle,
            marginBottom: 16,
            padding: "12px 16px",
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
            borderColor: "var(--yellow, #f59e0b)",
          }}
        >
          Knowledge is synced from Google Drive. Disconnect sync to edit
          documents manually.
        </div>
      )}

      {/* Upload drop zone */}
      <div
        onDragOver={(e) => {
          if (syncActive) return;
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          if (syncActive) return;
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => {
          if (syncActive) return;
          fileInputRef.current?.click();
        }}
        style={{
          ...cardStyle,
          marginBottom: 20,
          textAlign: "center",
          padding: "34px 20px",
          cursor: syncActive ? "not-allowed" : "pointer",
          opacity: syncActive ? 0.5 : 1,
          borderStyle: "dashed",
          borderColor: dragOver ? "var(--accent, #6366f1)" : "var(--border)",
          background: dragOver ? "rgba(99,102,241,0.08)" : cardStyle.background,
        }}
      >
        <p style={{ margin: 0, fontWeight: 600 }}>
          Drop files or a whole folder here
        </p>
        <p style={{ margin: "6px 0 0", fontSize: "0.85rem", color: "var(--text-muted)" }}>
          PDF, DOCX, TXT, Markdown. Up to 100 files at once - no more one-by-one uploads.
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          webkitdirectory=""
          style={{ display: "none" }}
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {/* Typed note card */}
      <div style={{ ...cardStyle, marginBottom: 20, opacity: syncActive ? 0.5 : 1 }}>
        <h3 style={{ margin: 0, fontSize: "1rem" }}>Type it in</h3>
        <p style={{ margin: "4px 0 12px", fontSize: "0.83rem", color: "var(--text-muted)" }}>
          No document handy? Type what your AI should know - pricing, policies,
          service details. Saving the same title again updates that note.
        </p>
        <input
          type="text"
          value={noteTitle}
          onChange={(e) => setNoteTitle(e.target.value)}
          placeholder='Title, e.g. "Cancellation policy"'
          maxLength={200}
          disabled={busy || syncActive}
          style={{
            width: "100%",
            boxSizing: "border-box",
            padding: "8px 12px",
            fontSize: "0.85rem",
            color: "var(--text-primary)",
            background: "var(--bg-primary)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            marginBottom: 8,
          }}
        />
        <textarea
          value={noteContent}
          onChange={(e) => setNoteContent(e.target.value)}
          placeholder="Appointments can be cancelled up to 24 hours in advance for a full refund…"
          rows={5}
          maxLength={100000}
          disabled={busy || syncActive}
          style={{
            width: "100%",
            boxSizing: "border-box",
            padding: "8px 12px",
            fontSize: "0.85rem",
            fontFamily: "inherit",
            color: "var(--text-primary)",
            background: "var(--bg-primary)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            resize: "vertical",
          }}
        />
        <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={saveNote}
            disabled={busy || syncActive || !noteTitle.trim() || !noteContent.trim()}
            title={syncActive ? "Disconnect Drive sync to edit documents" : undefined}
            style={{
              ...btnStyle,
              opacity: busy || syncActive || !noteTitle.trim() || !noteContent.trim() ? 0.5 : 1,
              cursor: syncActive ? "not-allowed" : "pointer",
            }}
          >
            Save to knowledge
          </button>
        </div>
      </div>

      {/* Drive connect card */}
      <div style={{ ...cardStyle, marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1rem" }}>Google Drive sync</h3>
            <p style={{ margin: "4px 0 0", fontSize: "0.83rem", color: "var(--text-muted)" }}>
              {drive?.connected
                ? drive.folder_name
                  ? `Syncing "${drive.folder_name}" daily. Last sync: ${formatDate(drive.last_synced_at)} (${drive.last_sync_status || "pending"})`
                  : "Connected - pick the folder to sync."
                : "Connect a Drive folder once; new and edited docs sync automatically every day."}
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {!drive?.connected && (
              <button onClick={connectDrive} disabled={busy} style={btnStyle}>
                Connect Google Drive
              </button>
            )}
            {drive?.connected && (
              <>
                <button onClick={openFolderPicker} disabled={busy} style={btnQuiet}>
                  {drive.folder_name ? "Change folder" : "Pick folder"}
                </button>
                {drive.folder_id && (
                  <button onClick={syncNow} disabled={busy} style={btnStyle}>
                    Sync now
                  </button>
                )}
                <button onClick={() => setConfirmDisconnect(true)} disabled={busy} style={btnQuiet}>
                  Disconnect
                </button>
              </>
            )}
          </div>
        </div>

        {folders && (
          <div style={{ marginTop: 14 }}>
            <p style={{ margin: "0 0 8px", fontSize: "0.83rem", color: "var(--text-muted)" }}>
              Choose the folder your AI should learn from:
            </p>
            {folders.length === 0 ? (
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                No folders found in this Drive.
              </p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {folders.map((f) => (
                  <button key={f.id} onClick={() => pickFolder(f)} disabled={busy} style={btnQuiet}>
                    {f.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {syncLog.length > 0 && (
          <div style={{ marginTop: 14, fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {syncLog.slice(0, 3).map((row, i) => (
              <div key={i}>
                {formatDate(row.synced_at)}: {row.files_added} added, {row.files_updated} updated,{" "}
                {row.files_skipped} skipped
                {row.files_pii_flagged > 0 ? `, ${row.files_pii_flagged} PII-flagged` : ""}
                {row.error ? ` \u2014 ${row.error}` : ""}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Local folder sync (CLI) card */}
      <div style={{ ...cardStyle, marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1rem" }}>Computer folder sync</h3>
            <p style={{ margin: "4px 0 0", fontSize: "0.83rem", color: "var(--text-muted)" }}>
              Keep a folder on your computer synced automatically - a tiny script
              watches it and uploads new or changed documents. Needs only Python.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <a
              href="/local-sync/anx_kb_sync.py"
              download
              style={{ ...btnQuiet, textDecoration: "none", display: "inline-block" }}
            >
              Download script
            </a>
            <button onClick={generateSyncCommand} disabled={busy} style={btnStyle}>
              Get sync command
            </button>
          </div>
        </div>

        {syncCmd && (
          <div style={{ marginTop: 14 }}>
            <p style={{ margin: "0 0 8px", fontSize: "0.83rem", color: "var(--text-muted)" }}>
              Run this next to the downloaded script (replace YOUR_FOLDER with the
              folder to sync). The token works for 180 days and only for knowledge
              sync - generate a new one here anytime.
            </p>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <pre
                style={{
                  flex: 1,
                  margin: 0,
                  padding: "10px 12px",
                  fontSize: "0.75rem",
                  overflowX: "auto",
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                }}
              >
                {syncCmd}
              </pre>
              <button onClick={copySyncCommand} style={btnQuiet}>
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Documents (the second brain index) */}
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>
            Source documents {docLimit ? `(${docs.length}/${docLimit})` : ""}
          </h3>
        </div>

        {loading ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Loading…</p>
        ) : docs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "30px 16px" }}>
            <p style={{ fontWeight: 600, margin: "0 0 6px" }}>No knowledge sources yet</p>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0 }}>
              Drop your price lists, FAQs, and playbooks above, or connect Google Drive.
              Your AI starts answering from them immediately.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto", marginTop: 10 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--text-muted)", fontSize: "0.75rem" }}>
                  <th style={{ padding: "6px 10px" }}>Document</th>
                  <th style={{ padding: "6px 10px" }}>Source</th>
                  <th style={{ padding: "6px 10px" }}>Size</th>
                  <th style={{ padding: "6px 10px" }}>Synced</th>
                  <th style={{ padding: "6px 10px" }}></th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr key={doc.id} style={{ borderTop: "1px solid var(--border)" }}>
                    <td style={{ padding: "8px 10px", color: "var(--text-primary)" }}>
                      {doc.filename}
                      {doc.pii_flags > 0 && (
                        <span
                          title="Possible sensitive data detected - review this document"
                          style={{ marginLeft: 8, fontSize: "0.72rem", color: "var(--yellow, #f59e0b)" }}
                        >
                          PII?
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "8px 10px", color: "var(--text-secondary)" }}>
                      {SOURCE_LABELS[doc.source] || doc.source}
                    </td>
                    <td style={{ padding: "8px 10px", color: "var(--text-muted)" }}>
                      {Math.max(1, Math.round(doc.chars / 1000))}k chars
                    </td>
                    <td style={{ padding: "8px 10px", color: "var(--text-muted)" }}>
                      {formatDate(doc.synced_at)}
                    </td>
                    <td style={{ padding: "8px 10px", textAlign: "right" }}>
                      <button
                        onClick={() => removeDoc(doc)}
                        disabled={busy || syncActive}
                        title={syncActive ? "Disconnect Drive sync to edit documents" : undefined}
                        style={{
                          ...btnQuiet,
                          padding: "4px 10px",
                          fontSize: "0.78rem",
                          opacity: syncActive ? 0.4 : 1,
                          cursor: syncActive ? "not-allowed" : "pointer",
                        }}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {confirmDisconnect && (
        <div
          onClick={() => setConfirmDisconnect(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 16,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ ...cardStyle, width: "100%", maxWidth: 420 }}
          >
            <h3 style={{ margin: 0, fontSize: "1.05rem" }}>Disconnect Google Drive?</h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "10px 0 0" }}>
              New and edited Drive docs stop syncing. Documents already synced
              stay in your knowledge base, and you can edit manually again.
            </p>
            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <button onClick={handleDisconnect} disabled={busy} style={btnStyle}>
                Disconnect
              </button>
              <button onClick={() => setConfirmDisconnect(false)} style={btnQuiet}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
