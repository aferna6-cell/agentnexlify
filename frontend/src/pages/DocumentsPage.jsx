import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchDocuments, createDocument, sendDocument, deleteDocument,
  fetchDocTemplates, createDocTemplate,
} from "../utils/api/documents";
import { fetchLeads } from "../utils/api/leads";

const STATUS_FILTERS = ["all", "draft", "sent", "viewed", "signed", "expired", "cancelled"];
const STATUS_COLORS = {
  draft: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
  sent: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  viewed: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  signed: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  expired: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  cancelled: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
};
const emptyForm = {
  title: "", html_content: "", signer_name: "", signer_email: "",
  signer_phone: "", lead_id: "", expiry_days: 30, notes: "",
};

function formatDate(dateStr) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function StatusBadge({ status }) {
  const sc = STATUS_COLORS[status] || STATUS_COLORS.draft;
  return (
    <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: "0.7rem", fontWeight: 600, color: sc.color, background: sc.bg, textTransform: "capitalize" }}>
      {status}
    </span>
  );
}

const overlay = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 };
const modalBase = { background: "var(--bg-primary)", borderRadius: 12, padding: 24, border: "1px solid var(--border-color)" };
const sectionLabel = { fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 };
const fieldLabel = { display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" };
const cancelBtn = { background: "transparent", border: "1px solid var(--border-color)", borderRadius: 8, padding: "8px 16px", color: "var(--text-primary)", cursor: "pointer" };
const warnBox = (c) => ({ marginBottom: 12, padding: "8px 12px", background: `rgba(${c},0.1)`, border: `1px solid rgba(${c},0.3)`, borderRadius: 8, fontSize: "0.8rem" });

export default function DocumentsPage() {
  const { user, token } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);
  const [leads, setLeads] = useState([]);
  const [loadingDropdowns, setLoadingDropdowns] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [detailDoc, setDetailDoc] = useState(null);
  const [showSendModal, setShowSendModal] = useState(false);
  const [sendTarget, setSendTarget] = useState(null);
  const [sendMethod, setSendMethod] = useState("email");
  const [sending, setSending] = useState(false);
  const [deletingIds, setDeletingIds] = useState(new Set());
  const [copiedId, setCopiedId] = useState(null);

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const params = {};
      if (activeFilter !== "all") params.status = activeFilter;
      const data = await fetchDocuments(user.tenantId, token, params);
      setDocuments(data.documents || data || []);
      setError(null);
    } catch (err) {
      console.warn("Failed to load documents:", err.message);
      setError(err.message || "Failed to load documents");
    } finally { setLoading(false); }
  }, [user?.tenantId, token, activeFilter]);

  useEffect(() => { setLoading(true); loadData(); }, [loadData]);

  const loadDropdowns = async () => {
    if (!user?.tenantId || loadingDropdowns) return;
    setLoadingDropdowns(true);
    try {
      const [leadsData, templatesData] = await Promise.all([
        fetchLeads(user.tenantId, token, { per_page: 200 }),
        fetchDocTemplates(user.tenantId, token).catch(() => []),
      ]);
      setLeads(leadsData.leads || []);
      setTemplates(Array.isArray(templatesData) ? templatesData : templatesData?.templates || []);
    } catch (err) { console.warn("Failed to load dropdowns:", err.message); }
    finally { setLoadingDropdowns(false); }
  };

  const openCreate = () => {
    setForm({ ...emptyForm }); setSelectedTemplateId(""); setShowModal(true); loadDropdowns();
  };

  const handleTemplateSelect = (templateId) => {
    setSelectedTemplateId(templateId);
    if (!templateId) return;
    const tmpl = templates.find((t) => t.id === templateId);
    if (tmpl) setForm((f) => ({ ...f, title: tmpl.name || f.title, html_content: tmpl.html_content || tmpl.content || f.html_content }));
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    const body = {
      title: form.title.trim(), html_content: form.html_content.trim() || null,
      signer_name: form.signer_name.trim() || null, signer_email: form.signer_email.trim() || null,
      signer_phone: form.signer_phone.trim() || null, lead_id: form.lead_id || null,
      expiry_days: Number(form.expiry_days) || 30, notes: form.notes.trim() || null,
    };
    try {
      await createDocument(user.tenantId, token, body);
      setShowModal(false); setForm({ ...emptyForm }); loadData();
    } catch (err) {
      console.warn("Save document failed:", err.message);
      setError(err.message || "Failed to save document");
    } finally { setSaving(false); }
  };

  const handleSaveAsTemplate = async () => {
    if (!form.title.trim() || !form.html_content.trim()) return;
    setSavingTemplate(true);
    try {
      const created = await createDocTemplate(user.tenantId, token, { name: form.title.trim(), html_content: form.html_content.trim() });
      setTemplates((prev) => [...prev, created]);
    } catch (err) {
      console.warn("Save template failed:", err.message);
      setError(err.message || "Failed to save template");
    } finally { setSavingTemplate(false); }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm("Delete this document? This cannot be undone.")) return;
    setDeletingIds((prev) => new Set(prev).add(docId));
    try {
      await deleteDocument(user.tenantId, token, docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      if (detailDoc?.id === docId) setDetailDoc(null);
      setError(null);
    } catch (err) {
      console.warn("Delete document failed:", err.message);
      setError(err.message || "Failed to delete document");
    } finally { setDeletingIds((prev) => { const n = new Set(prev); n.delete(docId); return n; }); }
  };

  const openSend = (doc, e) => {
    if (e) e.stopPropagation();
    setSendTarget(doc); setSendMethod("email"); setShowSendModal(true);
  };

  const handleSend = async () => {
    if (!sendTarget) return;
    setSending(true);
    try {
      await sendDocument(user.tenantId, token, sendTarget.id, { method: sendMethod });
      setShowSendModal(false); setSendTarget(null);
      setDocuments((prev) => prev.map((d) => (d.id === sendTarget.id ? { ...d, status: "sent" } : d)));
      if (detailDoc?.id === sendTarget.id) setDetailDoc((prev) => ({ ...prev, status: "sent" }));
    } catch (err) {
      console.warn("Send document failed:", err.message);
      setError(err.message || "Failed to send document");
    } finally { setSending(false); }
  };

  const handleCopyLink = (doc, e) => {
    if (e) e.stopPropagation();
    const link = doc.signing_url || `${window.location.origin}/sign/${doc.id}`;
    navigator.clipboard.writeText(link).then(() => {
      setCopiedId(doc.id); setTimeout(() => setCopiedId(null), 2000);
    }).catch(() => { setError("Failed to copy link to clipboard"); });
  };

  if (loading) return <SkeletonLoader />;

  const totalDocs = documents.length;
  const pendingCount = documents.filter((d) => d.status === "sent" || d.status === "viewed").length;
  const signedCount = documents.filter((d) => d.status === "signed").length;
  const draftCount = documents.filter((d) => d.status === "draft").length;
  const filteredDocs = activeFilter === "all" ? documents : documents.filter((d) => d.status === activeFilter);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Documents & E-Signatures</h1>
          <p>Create, send, and track documents for signing</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button className="btn-primary" onClick={() => { setLoading(true); loadData(); }} style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}>Refresh</button>
          <button className="btn-primary" onClick={openCreate}>+ New Document</button>
        </div>
      </div>

      {/* Stats Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Total Documents", value: totalDocs, color: "var(--text-secondary)" },
          { label: "Pending Signature", value: pendingCount, color: "#f59e0b" },
          { label: "Signed", value: signedCount, color: "#22c55e" },
          { label: "Draft", value: draftCount, color: "var(--text-muted)" },
        ].map((card) => (
          <div key={card.label} style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-color)", borderRadius: 12, padding: "16px 20px" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>{card.label}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Status Filter Tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {STATUS_FILTERS.map((s) => {
          const isActive = activeFilter === s;
          const count = s === "all" ? documents.length : documents.filter((d) => d.status === s).length;
          return (
            <button key={s} onClick={() => setActiveFilter(s)} style={{ padding: "8px 16px", borderRadius: 8, border: isActive ? "1px solid var(--accent)" : "1px solid var(--border-color)", background: isActive ? "var(--accent-dim)" : "var(--bg-secondary)", color: isActive ? "var(--accent)" : "var(--text-secondary)", cursor: "pointer", fontSize: "0.85rem", fontWeight: isActive ? 600 : 400, textTransform: "capitalize", transition: "all 0.15s ease" }}>
              {s}<span style={{ marginLeft: 6, fontSize: "0.75rem", opacity: 0.7 }}>{count}</span>
            </button>
          );
        })}
      </div>

      {error && (
        <div style={{ marginBottom: 16, padding: "10px 16px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, color: "#ef4444", fontSize: "0.85rem" }}>
          {error}
          <button onClick={() => setError(null)} style={{ marginLeft: 12, background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "0.8rem", textDecoration: "underline" }}>dismiss</button>
        </div>
      )}

      {/* Document List */}
      {filteredDocs.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            {activeFilter !== "all" ? "No documents match this filter" : "No documents yet"}
          </div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            {activeFilter !== "all"
              ? "Try selecting a different status filter, or create a new document."
              : "Create your first document to start collecting e-signatures. Add an HTML template, assign a signer, and send it via email or SMS."}
          </p>
          {activeFilter !== "all" ? (
            <button className="btn-primary" onClick={() => setActiveFilter("all")} style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}>Clear Filter</button>
          ) : (
            <button className="btn-primary" onClick={openCreate}>Create Your First Document</button>
          )}
        </div>
      ) : (
        <div style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-color)", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 100px 110px 160px", padding: "10px 16px", borderBottom: "1px solid var(--border-color)", fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            <span>Title</span><span>Signer</span>
            <span style={{ textAlign: "center" }}>Status</span>
            <span style={{ textAlign: "center" }}>Created</span>
            <span style={{ textAlign: "right" }}>Actions</span>
          </div>
          {filteredDocs.map((doc) => {
            const isDeleting = deletingIds.has(doc.id);
            const canSend = doc.status === "draft";
            const hasSentOrViewed = doc.status === "sent" || doc.status === "viewed";
            return (
              <div key={doc.id} onClick={() => setDetailDoc(doc)} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 100px 110px 160px", padding: "12px 16px", borderBottom: "1px solid var(--border-color)", alignItems: "center", cursor: "pointer", opacity: isDeleting ? 0.5 : 1, transition: "background 0.1s ease" }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "var(--hover-overlay)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent)" }}>{doc.title || "Untitled"}</span>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{doc.signer_name || doc.signer_email || "--"}</span>
                <span style={{ textAlign: "center" }}><StatusBadge status={doc.status} /></span>
                <span style={{ textAlign: "center", fontSize: "0.8rem", color: "var(--text-muted)" }}>{formatDate(doc.created_at)}</span>
                <div style={{ display: "flex", gap: 4, justifyContent: "flex-end" }} onClick={(e) => e.stopPropagation()}>
                  {canSend && (
                    <button onClick={(e) => openSend(doc, e)} style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.3)", borderRadius: 6, padding: "4px 10px", color: "#3b82f6", cursor: "pointer", fontSize: "0.75rem", fontWeight: 600 }}>Send</button>
                  )}
                  {hasSentOrViewed && (
                    <button onClick={(e) => handleCopyLink(doc, e)} style={{ background: copiedId === doc.id ? "rgba(34,197,94,0.1)" : "none", border: "1px solid var(--border-color)", borderRadius: 6, padding: "4px 8px", color: copiedId === doc.id ? "#22c55e" : "var(--text-secondary)", cursor: "pointer", fontSize: "0.75rem" }}>
                      {copiedId === doc.id ? "Copied!" : "Link"}
                    </button>
                  )}
                  {canSend && (
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }} disabled={isDeleting} style={{ background: "none", border: "1px solid var(--border-color)", borderRadius: 6, padding: "4px 8px", color: "#ef4444", cursor: "pointer", fontSize: "0.75rem" }}>
                      {isDeleting ? "..." : "Del"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Document Detail Modal */}
      {detailDoc && (
        <div style={overlay} onClick={() => setDetailDoc(null)}>
          <div style={{ ...modalBase, width: "90%", maxWidth: 620, maxHeight: "85vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h3 style={{ marginBottom: 6 }}>{detailDoc.title || "Untitled Document"}</h3>
                <StatusBadge status={detailDoc.status} />
              </div>
              <button onClick={() => setDetailDoc(null)} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}>x</button>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={sectionLabel}>Signer Details</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                {detailDoc.signer_name && <div><strong>Name:</strong> {detailDoc.signer_name}</div>}
                {detailDoc.signer_email && <div><strong>Email:</strong> {detailDoc.signer_email}</div>}
                {detailDoc.signer_phone && <div><strong>Phone:</strong> {detailDoc.signer_phone}</div>}
                {!detailDoc.signer_name && !detailDoc.signer_email && !detailDoc.signer_phone && (
                  <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>No signer assigned</div>
                )}
              </div>
            </div>

            <div style={{ display: "flex", gap: 20, marginBottom: 16, fontSize: "0.85rem", color: "var(--text-secondary)", flexWrap: "wrap" }}>
              {detailDoc.created_at && <div><strong>Created:</strong> {formatDate(detailDoc.created_at)}</div>}
              {detailDoc.sent_at && <div><strong>Sent:</strong> {formatDate(detailDoc.sent_at)}</div>}
              {detailDoc.signed_at && <div><strong>Signed:</strong> {formatDate(detailDoc.signed_at)}</div>}
              {detailDoc.expires_at && <div><strong>Expires:</strong> {formatDate(detailDoc.expires_at)}</div>}
            </div>

            {(detailDoc.status === "sent" || detailDoc.status === "viewed") && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ ...sectionLabel, marginBottom: 4 }}>Signing Link</div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input readOnly value={detailDoc.signing_url || `${window.location.origin}/sign/${detailDoc.id}`} style={{ flex: 1, fontSize: "0.8rem", background: "var(--bg-secondary)", color: "var(--text-secondary)" }} />
                  <button onClick={() => handleCopyLink(detailDoc)} style={{ background: copiedId === detailDoc.id ? "rgba(34,197,94,0.1)" : "var(--bg-secondary)", border: "1px solid var(--border-color)", borderRadius: 6, padding: "6px 12px", color: copiedId === detailDoc.id ? "#22c55e" : "var(--text-secondary)", cursor: "pointer", fontSize: "0.8rem", whiteSpace: "nowrap" }}>
                    {copiedId === detailDoc.id ? "Copied!" : "Copy Link"}
                  </button>
                </div>
              </div>
            )}

            {detailDoc.notes && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ ...sectionLabel, marginBottom: 4 }}>Notes</div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>{detailDoc.notes}</div>
              </div>
            )}

            {detailDoc.html_content && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ ...sectionLabel, marginBottom: 4 }}>Document Preview</div>
                <div style={{ background: "#fff", color: "#1a1a1a", borderRadius: 8, padding: 16, maxHeight: 300, overflowY: "auto", border: "1px solid var(--border-color)", fontSize: "0.85rem", lineHeight: 1.6 }}
                  dangerouslySetInnerHTML={{ __html: detailDoc.html_content }} />
              </div>
            )}

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", borderTop: "1px solid var(--border-color)", paddingTop: 16 }}>
              {detailDoc.status === "draft" && (
                <>
                  <button onClick={() => { setDetailDoc(null); openSend(detailDoc); }} style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.3)", borderRadius: 8, padding: "8px 16px", color: "#3b82f6", cursor: "pointer", fontSize: "0.85rem", fontWeight: 600 }}>Send Document</button>
                  <button onClick={() => { setDetailDoc(null); handleDelete(detailDoc.id); }} style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, padding: "8px 16px", color: "#ef4444", cursor: "pointer", fontSize: "0.85rem", fontWeight: 600 }}>Delete</button>
                </>
              )}
              <button onClick={() => setDetailDoc(null)} className="btn-primary">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Document Modal */}
      {showModal && (
        <div style={overlay} onClick={() => setShowModal(false)}>
          <div style={{ ...modalBase, width: "90%", maxWidth: 640, maxHeight: "88vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: 16 }}>Create Document</h3>

            {templates.length > 0 && (
              <div style={{ background: "rgba(139,92,246,0.08)", border: "1px solid rgba(139,92,246,0.2)", borderRadius: 8, padding: 12, marginBottom: 16 }}>
                <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#8b5cf6", marginBottom: 8 }}>Start from Template</div>
                <select value={selectedTemplateId} onChange={(e) => handleTemplateSelect(e.target.value)} style={{ width: "100%", fontSize: "0.85rem" }}>
                  <option value="">Blank document</option>
                  {templates.map((tmpl) => <option key={tmpl.id} value={tmpl.id}>{tmpl.name}</option>)}
                </select>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 4 }}>Select a saved template to pre-fill the document content</div>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={fieldLabel}>Document Title *</label>
                <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} placeholder="e.g. Service Agreement, NDA, Consent Form" style={{ width: "100%" }} />
              </div>

              <div>
                <label style={fieldLabel}>Document Content (HTML)</label>
                <textarea value={form.html_content} onChange={(e) => setForm((f) => ({ ...f, html_content: e.target.value }))} placeholder={"<h2>Service Agreement</h2>\n<p>This agreement is entered into by...</p>\n<p>Signature: _______________</p>"} rows={8} style={{ width: "100%", resize: "vertical", fontFamily: "monospace", fontSize: "0.8rem" }} />
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 4 }}>Use HTML tags for formatting. The signer will see this as a formatted document.</div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={fieldLabel}>Signer Name</label>
                  <input value={form.signer_name} onChange={(e) => setForm((f) => ({ ...f, signer_name: e.target.value }))} placeholder="John Smith" style={{ width: "100%" }} />
                </div>
                <div>
                  <label style={fieldLabel}>Signer Email</label>
                  <input type="email" value={form.signer_email} onChange={(e) => setForm((f) => ({ ...f, signer_email: e.target.value }))} placeholder="john@example.com" style={{ width: "100%" }} />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={fieldLabel}>Signer Phone</label>
                  <input type="tel" value={form.signer_phone} onChange={(e) => setForm((f) => ({ ...f, signer_phone: e.target.value }))} placeholder="+1 555-123-4567" style={{ width: "100%" }} />
                </div>
                <div>
                  <label style={fieldLabel}>Expiry (days)</label>
                  <input type="number" value={form.expiry_days} onChange={(e) => setForm((f) => ({ ...f, expiry_days: e.target.value }))} min={1} max={365} style={{ width: "100%" }} />
                </div>
              </div>

              <div>
                <label style={fieldLabel}>Link to Lead (optional)</label>
                {loadingDropdowns ? (
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Loading leads...</div>
                ) : (
                  <select value={form.lead_id} onChange={(e) => {
                    const leadId = e.target.value;
                    setForm((f) => ({ ...f, lead_id: leadId }));
                    if (leadId) {
                      const lead = leads.find((l) => l.id === leadId);
                      if (lead) setForm((f) => ({ ...f, lead_id: leadId, signer_name: f.signer_name || lead.name || "", signer_email: f.signer_email || lead.email || "", signer_phone: f.signer_phone || lead.phone || "" }));
                    }
                  }} style={{ width: "100%" }}>
                    <option value="">No lead linked</option>
                    {leads.map((lead) => <option key={lead.id} value={lead.id}>{lead.name || lead.email || lead.phone || lead.id}</option>)}
                  </select>
                )}
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 4 }}>Selecting a lead will auto-fill signer details if they are empty</div>
              </div>

              <div>
                <label style={fieldLabel}>Internal Notes</label>
                <textarea value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Internal notes about this document (not visible to signer)..." rows={2} style={{ width: "100%", resize: "vertical" }} />
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
              {form.title.trim() && form.html_content.trim() && (
                <button onClick={handleSaveAsTemplate} disabled={savingTemplate} style={{ background: "transparent", border: "1px solid rgba(139,92,246,0.4)", borderRadius: 8, padding: "8px 16px", color: "#8b5cf6", cursor: "pointer", fontSize: "0.8rem", marginRight: "auto" }}>
                  {savingTemplate ? "Saving..." : "Save as Template"}
                </button>
              )}
              <button onClick={() => setShowModal(false)} style={cancelBtn}>Cancel</button>
              <button className="btn-primary" onClick={handleSave} disabled={!form.title.trim() || saving}>
                {saving ? "Creating..." : "Create Document"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Send Document Modal */}
      {showSendModal && sendTarget && (
        <div style={{ ...overlay, zIndex: 1100 }} onClick={() => setShowSendModal(false)}>
          <div style={{ ...modalBase, width: "90%", maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: 4 }}>Send Document for Signing</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 20 }}>
              {sendTarget.title}{sendTarget.signer_name ? ` -- to ${sendTarget.signer_name}` : ""}
            </p>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 10, fontWeight: 600 }}>Send Method</div>
              {["email", "sms", "both"].map((method) => (
                <label key={method} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, cursor: "pointer" }}>
                  <input type="radio" name="send-doc-method" value={method} checked={sendMethod === method} onChange={() => setSendMethod(method)} style={{ width: "auto" }} />
                  <span style={{ fontSize: "0.9rem", textTransform: "capitalize" }}>{method === "both" ? "Email + SMS" : method.toUpperCase()}</span>
                </label>
              ))}
            </div>

            <div style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-color)", borderRadius: 8, padding: 12, marginBottom: 20, fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              <strong>What happens next:</strong><br />
              The signer will receive a link to view and sign the document.
              {(sendMethod === "email" || sendMethod === "both") && " An email with the signing link and document preview will be sent."}
              {(sendMethod === "sms" || sendMethod === "both") && " An SMS with the signing link will be sent."}
              {" "}You will be notified when the document is viewed or signed.
            </div>

            {sendMethod !== "sms" && !sendTarget.signer_email && (
              <div style={{ ...warnBox("245,158,11"), color: "#f59e0b" }}>No signer email set. Email delivery will fail. Edit the document to add an email address first.</div>
            )}
            {sendMethod !== "email" && !sendTarget.signer_phone && (
              <div style={{ ...warnBox("245,158,11"), color: "#f59e0b" }}>No signer phone set. SMS delivery will fail. Edit the document to add a phone number first.</div>
            )}

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setShowSendModal(false)} style={cancelBtn}>Cancel</button>
              <button className="btn-primary" onClick={handleSend} disabled={sending}>
                {sending ? "Sending..." : "Send Document"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
