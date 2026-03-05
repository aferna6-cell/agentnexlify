import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchLeadScore } from "../../utils/api";

const STAGE_OPTIONS = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "appointment_booked", label: "Appointment" },
  { value: "closed", label: "Closed" },
  { value: "lost", label: "Lost" },
];

function scoreClass(score) {
  if (score >= 80) return "score-hot";
  if (score >= 60) return "score-warm";
  if (score >= 40) return "score-cool";
  return "score-cold";
}

function scoreLabel(score) {
  if (score >= 80) return "Hot";
  if (score >= 60) return "Warm";
  if (score >= 40) return "Cool";
  return "Cold";
}

function scoreColor(score) {
  if (score >= 80) return "var(--red)";
  if (score >= 60) return "var(--yellow)";
  if (score >= 40) return "var(--accent)";
  return "var(--text-muted)";
}

function ScoreBreakdown({ breakdown }) {
  if (!breakdown) return null;
  const eng = breakdown.engagement?.total || 0;
  const int = breakdown.intent?.total || 0;
  const rec = breakdown.recency?.total || 0;
  const dec = breakdown.decay?.total || 0;
  const total = eng + int + rec;

  return (
    <div className="score-breakdown">
      <div className="score-stacked-bar">
        {total > 0 && (
          <>
            <div className="bar-segment engagement" style={{ width: `${(eng / total) * 100}%` }} />
            <div className="bar-segment intent" style={{ width: `${(int / total) * 100}%` }} />
            <div className="bar-segment recency" style={{ width: `${(rec / total) * 100}%` }} />
          </>
        )}
      </div>
      <div className="score-category-row">
        <span className="score-category-left"><span className="score-dot engagement" /> <span className="score-category-label">Engagement</span></span>
        <span className="score-category-value">{eng} / {breakdown.engagement?.max || 40}</span>
      </div>
      <div className="score-category-row">
        <span className="score-category-left"><span className="score-dot intent" /> <span className="score-category-label">Intent</span></span>
        <span className="score-category-value">{int} / {breakdown.intent?.max || 40}</span>
      </div>
      <div className="score-category-row">
        <span className="score-category-left"><span className="score-dot recency" /> <span className="score-category-label">Recency</span></span>
        <span className="score-category-value">{rec} / {breakdown.recency?.max || 20}</span>
      </div>
      {dec > 0 && (
        <div className="score-category-row">
          <span className="score-category-left"><span className="score-dot decay" /> <span className="score-category-label">Decay</span></span>
          <span className="score-category-value decay">-{dec}</span>
        </div>
      )}
    </div>
  );
}

export default function LeadDetailDrawer({ lead, onClose, onSave, onDelete }) {
  const { user, token } = useAuth();
  const [breakdown, setBreakdown] = useState(null);
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    conversation_summary: "",
    status: "new",
    areas_of_interest: "",
    timeline: "",
    budget: "",
  });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setForm({
      name: lead.name || "",
      email: lead.email || "",
      phone: lead.phone || "",
      conversation_summary: lead.conversation_summary || "",
      status: lead.status || "new",
      areas_of_interest: lead.areas_of_interest || "",
      timeline: lead.timeline || "",
      budget: lead.budget || "",
    });
    setConfirmDelete(false);
    setBreakdown(null);
    if (user?.tenantId && lead.id && token) {
      fetchLeadScore(user.tenantId, lead.id, token)
        .then((data) => setBreakdown(data.breakdown))
        .catch(() => {});
    }
  }, [lead, user?.tenantId, token]);

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
  };

  const handleSave = async () => {
    if (!onSave) return;
    setSaving(true);
    try {
      const updates = {};
      for (const [k, v] of Object.entries(form)) {
        const original = lead[k] || "";
        if (v !== original) updates[k] = v || null;
      }
      if (Object.keys(updates).length > 0) {
        await onSave(lead.id, updates);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    if (onDelete) await onDelete(lead.id);
  };

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2 className="drawer-title">Edit Lead</h2>
          <button className="drawer-close" onClick={onClose}>&times;</button>
        </div>

        <div className="drawer-body">
          {/* Score (read-only) */}
          <div className="lead-score-display">
            <div>
              <div className="lead-score-label">Lead Score</div>
              <div className="lead-score-value" style={{ color: scoreColor(lead.lead_score) }}>
                {lead.lead_score ?? "N/A"} / 100
              </div>
            </div>
            <span
              className={`lead-tag ${scoreClass(lead.lead_score)}`}
              style={{ marginLeft: "auto", fontSize: 13 }}
            >
              {scoreLabel(lead.lead_score)}
            </span>
          </div>

          <ScoreBreakdown breakdown={breakdown} />

          {/* Editable fields */}
          <div className="intel-section">
            <div className="intel-title">Contact Info</div>
            <div className="drawer-field">
              <label className="drawer-label">Name</label>
              <input className="drawer-input" value={form.name} onChange={handleChange("name")} placeholder="Lead name" />
            </div>
            <div className="drawer-field">
              <label className="drawer-label">Email</label>
              <input className="drawer-input" type="email" value={form.email} onChange={handleChange("email")} placeholder="email@example.com" />
            </div>
            <div className="drawer-field">
              <label className="drawer-label">Phone</label>
              <input className="drawer-input" type="tel" value={form.phone} onChange={handleChange("phone")} placeholder="(555) 123-4567" />
            </div>
          </div>

          <div className="intel-section">
            <div className="intel-title">Details</div>
            <div className="drawer-field">
              <label className="drawer-label">Stage</label>
              <select className="drawer-select" value={form.status} onChange={handleChange("status")}>
                {STAGE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div className="drawer-field">
              <label className="drawer-label">Areas of Interest</label>
              <input className="drawer-input" value={form.areas_of_interest} onChange={handleChange("areas_of_interest")} placeholder="Areas of interest" />
            </div>
            <div className="drawer-field">
              <label className="drawer-label">Timeline</label>
              <input className="drawer-input" value={form.timeline} onChange={handleChange("timeline")} placeholder="Timeline" />
            </div>
            <div className="drawer-field">
              <label className="drawer-label">Budget</label>
              <input className="drawer-input" value={form.budget} onChange={handleChange("budget")} placeholder="Budget" />
            </div>
            <div className="drawer-field">
              <label className="drawer-label">Notes</label>
              <textarea className="drawer-textarea" value={form.conversation_summary} onChange={handleChange("conversation_summary")} placeholder="Add notes..." rows={3} />
            </div>
          </div>

          {/* Read-only metadata */}
          <div className="intel-section">
            <div className="intel-title">Info</div>
            <div className="intel-row">
              <span className="intel-label">Temperature</span>
              <span className="intel-value">{lead.lead_temperature || "-"}</span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Created</span>
              <span className="intel-value">
                {lead.created_at ? new Date(lead.created_at).toLocaleDateString("en-US", {
                  month: "short", day: "numeric", year: "numeric",
                }) : "Unknown"}
              </span>
            </div>
            {lead.conversation_id && (
              <div className="intel-row">
                <span className="intel-label">Conversation</span>
                <span className="intel-value" style={{ color: "var(--accent)" }}>Linked</span>
              </div>
            )}
          </div>
        </div>

        <div className="drawer-footer">
          <button
            className={`drawer-btn drawer-btn-danger${confirmDelete ? " confirming" : ""}`}
            onClick={handleDelete}
          >
            {confirmDelete ? "Confirm Delete" : "Delete"}
          </button>
          <button
            className="drawer-btn drawer-btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
