import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchLeadScore, sendLeadEmail, sendLeadSms, assignLead, fetchTeamMembers, fetchFieldDefinitions, fetchLeadFieldValues, updateLeadFieldValues, requestReviewForLead } from "../../utils/api";

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

function temperatureBadge(temp) {
  if (!temp) return null;
  const t = temp.toLowerCase();
  const config = {
    hot: { color: "#ff4444", bg: "rgba(255, 68, 68, 0.15)", border: "rgba(255, 68, 68, 0.3)" },
    warm: { color: "#f5a623", bg: "rgba(245, 166, 35, 0.15)", border: "rgba(245, 166, 35, 0.3)" },
    cold: { color: "#00bfff", bg: "rgba(0, 191, 255, 0.15)", border: "rgba(0, 191, 255, 0.3)" },
  };
  const c = config[t] || config.cold;
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "3px 10px",
      borderRadius: 12,
      fontSize: "0.75rem",
      fontWeight: 600,
      background: c.bg,
      color: c.color,
      border: `1px solid ${c.border}`,
    }}>
      {t === "hot" ? (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v10m0 0l-3-3m3 3l3-3M5 21a7 7 0 0114 0" /><circle cx="12" cy="17" r="4" fill="currentColor" opacity="0.3" /></svg>
      ) : t === "warm" ? (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" /></svg>
      ) : (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M20 17.58A11 11 0 0 0 18 4.41C9.71 4.41 3 11.12 3 19.41h9.71" /><path d="M12.71 12.71L17 8.41" /></svg>
      )}
      {temp.charAt(0).toUpperCase() + temp.slice(1).toLowerCase()}
    </span>
  );
}

function GenericScoreFactors({ lead }) {
  const factors = [
    { label: "Has email", met: !!lead.email, points: 20 },
    { label: "Has phone", met: !!lead.phone, points: 15 },
    { label: "Has name", met: !!lead.name, points: 10 },
    { label: "Has conversation", met: !!lead.conversation_id || !!lead.session_id, points: 10 },
    { label: "Booked appointment", met: lead.status === "appointment_booked", points: 25 },
  ];
  const earned = factors.filter((f) => f.met).reduce((sum, f) => sum + f.points, 0);

  return (
    <div className="score-factors-section">
      <div className="score-factors-header">
        <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Score Factors
        </span>
        <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          {earned} pts from profile
        </span>
      </div>
      <div className="score-factors-list">
        {factors.map((f) => (
          <div key={f.label} className="score-factor-row">
            <span className="score-factor-left">
              {f.met ? (
                <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="10" fill="var(--green)" />
                  <path d="M6 10l3 3 5-6" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="10" fill="var(--border)" />
                  <path d="M7 7l6 6M13 7l-6 6" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              )}
              <span style={{ color: f.met ? "var(--text-primary)" : "var(--text-muted)", fontSize: "0.8rem" }}>
                {f.label}
              </span>
            </span>
            <span style={{
              fontSize: "0.78rem",
              fontWeight: 600,
              color: f.met ? "var(--green)" : "var(--text-muted)",
            }}>
              {f.met ? `+${f.points}` : `+${f.points}`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
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
    insurance_carrier: "",
    insurance_member_id: "",
    insurance_group: "",
    date_of_birth: "",
  });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showEmail, setShowEmail] = useState(false);
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailStatus, setEmailStatus] = useState(null);
  const [showSms, setShowSms] = useState(false);
  const [smsBody, setSmsBody] = useState("");
  const [sendingSms, setSendingSms] = useState(false);
  const [smsStatus, setSmsStatus] = useState(null);
  const [teamMembers, setTeamMembers] = useState([]);
  const [assignedTo, setAssignedTo] = useState(lead.assigned_to || "");
  const [sendingReview, setSendingReview] = useState(false);
  const [reviewStatus, setReviewStatus] = useState(null);

  // Custom Fields state
  const [customFieldDefs, setCustomFieldDefs] = useState([]);
  const [customFieldValues, setCustomFieldValues] = useState({});
  const [savingCustomFields, setSavingCustomFields] = useState(false);
  const [customFieldStatus, setCustomFieldStatus] = useState(null);

  useEffect(() => {
    if (user?.tenantId && token) {
      fetchTeamMembers(user.tenantId, token)
        .then((data) => setTeamMembers(data.members || []))
        .catch((err) => console.warn("Team members fetch failed:", err.message));
    }
  }, [user?.tenantId, token]);

  // Load custom field definitions + values for this lead
  useEffect(() => {
    if (!user?.tenantId || !token || !lead.id) return;
    Promise.all([
      fetchFieldDefinitions(user.tenantId, token).catch(() => null),
      fetchLeadFieldValues(user.tenantId, token, lead.id).catch(() => null),
    ]).then(([defs, vals]) => {
      setCustomFieldDefs(Array.isArray(defs) ? defs : (defs?.fields || []));
      setCustomFieldValues(vals && typeof vals === "object" ? vals : {});
    });
  }, [user?.tenantId, token, lead.id]);

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
      insurance_carrier: lead.insurance_carrier || "",
      insurance_member_id: lead.insurance_member_id || "",
      insurance_group: lead.insurance_group || "",
      date_of_birth: lead.date_of_birth || "",
    });
    setConfirmDelete(false);
    setBreakdown(null);
    setAssignedTo(lead.assigned_to || "");
    setShowEmail(false);
    setEmailSubject("");
    setEmailBody("");
    setEmailStatus(null);
    setCustomFieldValues({});
    setCustomFieldStatus(null);
    if (user?.tenantId && lead.id && token) {
      fetchLeadScore(user.tenantId, lead.id, token)
        .then((data) => setBreakdown(data.breakdown))
        .catch((err) => console.warn("Lead score fetch failed:", err.message));
    }
  }, [lead, user?.tenantId, token]);

  const handleSaveCustomFields = async () => {
    setSavingCustomFields(true);
    setCustomFieldStatus(null);
    try {
      await updateLeadFieldValues(user.tenantId, token, lead.id, customFieldValues);
      setCustomFieldStatus("saved");
    } catch (err) {
      setCustomFieldStatus(err.body?.detail || err.message || "Failed to save");
    } finally {
      setSavingCustomFields(false);
    }
  };

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

  const handleAssign = async (memberId) => {
    setAssignedTo(memberId);
    try {
      await assignLead(user.tenantId, token, lead.id, memberId || null);
    } catch (err) {
      setAssignedTo(lead.assigned_to || "");
      console.warn("Assign failed:", err.message);
    }
  };

  const handleSendEmail = async () => {
    if (!emailSubject.trim() || !emailBody.trim()) return;
    setSendingEmail(true);
    setEmailStatus(null);
    try {
      await sendLeadEmail(user.tenantId, token, lead.id, {
        subject: emailSubject,
        message: emailBody,
      });
      setEmailStatus("sent");
      setEmailSubject("");
      setEmailBody("");
      setShowEmail(false);
    } catch (err) {
      setEmailStatus(err.body?.detail || err.message || "Failed to send");
    } finally {
      setSendingEmail(false);
    }
  };

  const handleSendSms = async () => {
    if (!smsBody.trim()) return;
    setSendingSms(true);
    setSmsStatus(null);
    try {
      await sendLeadSms(user.tenantId, token, lead.id, smsBody);
      setSmsStatus("sent");
      setSmsBody("");
      setShowSms(false);
    } catch (err) {
      setSmsStatus(err.body?.detail || err.message || "Failed to send");
    } finally {
      setSendingSms(false);
    }
  };

  const handleRequestReview = async () => {
    setSendingReview(true);
    setReviewStatus(null);
    try {
      const result = await requestReviewForLead(user.tenantId, token, lead.id);
      setReviewStatus(`Review request sent via ${result.sent_via.join(" & ")}`);
    } catch (err) {
      setReviewStatus(err.body?.detail || err.message || "Failed to send review request");
    } finally {
      setSendingReview(false);
    }
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
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
              {lead.lead_temperature && temperatureBadge(lead.lead_temperature)}
              <span
                className={`lead-tag ${scoreClass(lead.lead_score)}`}
                style={{ fontSize: 13 }}
              >
                {scoreLabel(lead.lead_score)}
              </span>
            </div>
          </div>

          <ScoreBreakdown breakdown={breakdown} />
          {!breakdown && <GenericScoreFactors lead={lead} />}

          {/* Auto-tags */}
          {lead.tags && lead.tags.length > 0 && (
            <div className="intel-section">
              <div className="intel-title">Tags</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {lead.tags.map((tag, i) => (
                  <span key={i} style={{
                    display: "inline-block",
                    padding: "4px 10px",
                    borderRadius: 14,
                    fontSize: "0.78rem",
                    background: "var(--accent-dim, rgba(0,191,255,0.15))",
                    color: "var(--accent, #00BFFF)",
                    border: "1px solid var(--accent-dim, rgba(0,191,255,0.25))",
                  }}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Unsubscribe status */}
          {lead.unsubscribed && (
            <div className="intel-section">
              <div style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 12px",
                borderRadius: 8,
                fontSize: "0.8rem",
                fontWeight: 600,
                background: "rgba(239,68,68,0.15)",
                color: "#ef4444",
                border: "1px solid rgba(239,68,68,0.3)",
              }}>
                Unsubscribed{lead.unsubscribed_at ? ` on ${new Date(lead.unsubscribed_at).toLocaleDateString()}` : ""}
              </div>
            </div>
          )}

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
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input className="drawer-input" type="tel" value={form.phone} onChange={handleChange("phone")} placeholder="(555) 123-4567" style={{ flex: 1 }} />
                {form.phone && (
                  <a href={`tel:${form.phone}`} title="Call" style={{ color: "var(--accent)", fontSize: "1.1rem", textDecoration: "none", flexShrink: 0 }}>
                    &#9742;
                  </a>
                )}
              </div>
            </div>
            <div className="drawer-field">
              <label className="drawer-label">Date of Birth</label>
              <input className="drawer-input" type="date" value={form.date_of_birth} onChange={handleChange("date_of_birth")} />
            </div>
          </div>

          {/* Quick Follow-up */}
          {(form.email || form.phone) && (
            <div className="intel-section">
              <div className="intel-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                Quick Follow-up
                <div style={{ display: "flex", gap: 6 }}>
                  {form.email && !showEmail && !showSms && (
                    <button className="btn-sm" onClick={() => { setShowEmail(true); setShowSms(false); }}>Email</button>
                  )}
                  {form.phone && !showSms && !showEmail && (
                    <button className="btn-sm" onClick={() => { setShowSms(true); setShowEmail(false); }} style={{ background: "var(--green, #22c55e)" }}>SMS</button>
                  )}
                  {!showEmail && !showSms && (
                    <button
                      className="btn-sm"
                      onClick={handleRequestReview}
                      disabled={sendingReview}
                      style={{ background: "var(--purple, #8b5cf6)" }}
                      title="Send a review request via email and/or SMS"
                    >
                      {sendingReview ? "Sending..." : "Request Review"}
                    </button>
                  )}
                </div>
              </div>
              {emailStatus === "sent" && (
                <div style={{ color: "var(--green, #22c55e)", fontSize: "0.85rem", marginBottom: 8 }}>Email sent successfully</div>
              )}
              {emailStatus && emailStatus !== "sent" && (
                <div style={{ color: "var(--red, #ef4444)", fontSize: "0.85rem", marginBottom: 8 }}>{emailStatus}</div>
              )}
              {smsStatus === "sent" && (
                <div style={{ color: "var(--green, #22c55e)", fontSize: "0.85rem", marginBottom: 8 }}>SMS sent successfully</div>
              )}
              {smsStatus && smsStatus !== "sent" && (
                <div style={{ color: "var(--red, #ef4444)", fontSize: "0.85rem", marginBottom: 8 }}>{smsStatus}</div>
              )}
              {reviewStatus && (
                <div style={{ color: reviewStatus.startsWith("Review request sent") ? "var(--green, #22c55e)" : "var(--red, #ef4444)", fontSize: "0.85rem", marginBottom: 8 }}>{reviewStatus}</div>
              )}
              {showEmail && (
                <>
                  <div className="drawer-field">
                    <label className="drawer-label">Subject</label>
                    <input className="drawer-input" value={emailSubject} onChange={(e) => setEmailSubject(e.target.value)} placeholder="Follow-up on your inquiry" />
                  </div>
                  <div className="drawer-field">
                    <label className="drawer-label">Message</label>
                    <textarea className="drawer-textarea" value={emailBody} onChange={(e) => setEmailBody(e.target.value)} placeholder="Write your message..." rows={4} />
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    <button className="btn-sm" onClick={handleSendEmail} disabled={sendingEmail || !emailSubject.trim() || !emailBody.trim()}>
                      {sendingEmail ? "Sending..." : "Send Email"}
                    </button>
                    <button className="btn-sm" onClick={() => setShowEmail(false)} style={{ background: "var(--bg-darker, #1a1a2e)" }}>
                      Cancel
                    </button>
                  </div>
                </>
              )}
              {showSms && (
                <>
                  <div className="drawer-field">
                    <label className="drawer-label">Text Message</label>
                    <textarea className="drawer-textarea" value={smsBody} onChange={(e) => setSmsBody(e.target.value)} placeholder="Hi, just following up on your inquiry..." rows={3} maxLength={1600} />
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    <button className="btn-sm" onClick={handleSendSms} disabled={sendingSms || !smsBody.trim()} style={{ background: "var(--green, #22c55e)" }}>
                      {sendingSms ? "Sending..." : "Send SMS"}
                    </button>
                    <button className="btn-sm" onClick={() => setShowSms(false)} style={{ background: "var(--bg-darker, #1a1a2e)" }}>
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

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
              <label className="drawer-label">Assigned To</label>
              <select className="drawer-select" value={assignedTo} onChange={(e) => handleAssign(e.target.value)}>
                <option value="">Unassigned</option>
                {teamMembers.map((m) => (
                  <option key={m.id} value={m.id}>{m.name || m.email}</option>
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

          {/* Insurance (shown for all leads — useful for dental/medical) */}
          {(form.insurance_carrier || form.insurance_member_id || form.insurance_group || lead.insurance_carrier) ? (
            <div className="intel-section">
              <div className="intel-title">Insurance</div>
              <div className="drawer-field">
                <label className="drawer-label">Carrier</label>
                <input className="drawer-input" value={form.insurance_carrier} onChange={handleChange("insurance_carrier")} placeholder="e.g. Delta Dental, Cigna" />
              </div>
              <div className="drawer-field">
                <label className="drawer-label">Member ID</label>
                <input className="drawer-input" value={form.insurance_member_id} onChange={handleChange("insurance_member_id")} placeholder="Member/Policy ID" />
              </div>
              <div className="drawer-field">
                <label className="drawer-label">Group Number</label>
                <input className="drawer-input" value={form.insurance_group} onChange={handleChange("insurance_group")} placeholder="Group #" />
              </div>
            </div>
          ) : null}

          {/* Custom Fields */}
          {customFieldDefs.length > 0 && (
            <div className="intel-section">
              <div className="intel-title">Custom Fields</div>
              {customFieldDefs.map((field) => {
                const fieldId = field.id;
                const currentVal = customFieldValues[fieldId] !== undefined ? customFieldValues[fieldId] : "";
                const onChange = (val) => setCustomFieldValues((prev) => ({ ...prev, [fieldId]: val }));

                return (
                  <div key={fieldId} className="drawer-field">
                    <label className="drawer-label">
                      {field.name}
                      {field.is_required && (
                        <span style={{ color: "#f87171", marginLeft: 4 }}>*</span>
                      )}
                    </label>
                    {field.field_type === "text" && (
                      <input
                        className="drawer-input"
                        value={currentVal}
                        onChange={(e) => onChange(e.target.value)}
                        placeholder={field.name}
                      />
                    )}
                    {field.field_type === "number" && (
                      <input
                        className="drawer-input"
                        type="number"
                        value={currentVal}
                        onChange={(e) => onChange(e.target.value)}
                        placeholder="0"
                      />
                    )}
                    {field.field_type === "date" && (
                      <input
                        className="drawer-input"
                        type="date"
                        value={currentVal}
                        onChange={(e) => onChange(e.target.value)}
                      />
                    )}
                    {field.field_type === "checkbox" && (
                      <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                        <input
                          type="checkbox"
                          checked={!!currentVal}
                          onChange={(e) => onChange(e.target.checked)}
                          style={{ width: "auto" }}
                        />
                        {field.name}
                      </label>
                    )}
                    {field.field_type === "dropdown" && (
                      <select
                        className="drawer-select"
                        value={currentVal}
                        onChange={(e) => onChange(e.target.value)}
                      >
                        <option value="">-- Select --</option>
                        {(field.options || []).map((opt) => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    )}
                  </div>
                );
              })}

              {customFieldStatus === "saved" && (
                <div style={{ color: "var(--green, #22c55e)", fontSize: "0.85rem", marginTop: 4 }}>
                  Custom fields saved
                </div>
              )}
              {customFieldStatus && customFieldStatus !== "saved" && (
                <div style={{ color: "#f87171", fontSize: "0.85rem", marginTop: 4 }}>
                  {customFieldStatus}
                </div>
              )}

              <button
                className="btn-secondary"
                onClick={handleSaveCustomFields}
                disabled={savingCustomFields}
                style={{ marginTop: 10, fontSize: "0.85rem" }}
              >
                {savingCustomFields ? "Saving..." : "Save Custom Fields"}
              </button>
            </div>
          )}

          {/* Read-only metadata */}
          <div className="intel-section">
            <div className="intel-title">Info</div>
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
