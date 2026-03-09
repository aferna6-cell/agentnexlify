import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  fetchClientProfile,
  fetchClientTimeline,
  addClientNote,
  changeClientStage,
  updateClient,
  sendSms,
} from "../../utils/api";
import SkeletonLoader from "../../components/SkeletonLoader";

const STAGES = ["new", "contacted", "appointment_booked", "closed", "lost"];

function scoreLabel(score) {
  if (score >= 70) return "hot";
  if (score >= 40) return "warm";
  return "cold";
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function ClientProfile({ onNavigate, pageData }) {
  const { user, token } = useAuth();
  const leadId = pageData?.leadId;
  const [profile, setProfile] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [noteText, setNoteText] = useState("");
  const [saving, setSaving] = useState(false);
  const [timelineOffset, setTimelineOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [editing, setEditing] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [showSmsModal, setShowSmsModal] = useState(false);
  const [smsPhone, setSmsPhone] = useState("");
  const [smsMessage, setSmsMessage] = useState("");
  const [smsSending, setSmsSending] = useState(false);
  const [smsResult, setSmsResult] = useState(null);

  const load = useCallback(async () => {
    if (!user?.tenantId || !leadId) return;
    setLoading(true);
    try {
      const [profileRes, timelineRes] = await Promise.all([
        fetchClientProfile(user.tenantId, leadId, token),
        fetchClientTimeline(user.tenantId, leadId, token),
      ]);
      setProfile(profileRes);
      setTimeline(timelineRes.timeline || []);
      setHasMore(timelineRes.has_more || false);
      setTimelineOffset(timelineRes.timeline?.length || 0);
    } catch (err) {
      console.error("Failed to load client profile", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, leadId, token]);

  useEffect(() => {
    load();
  }, [load]);

  const handleStageChange = async (stage) => {
    if (!user?.tenantId) return;
    try {
      await changeClientStage(user.tenantId, leadId, token, stage);
      setProfile((p) => (p ? { ...p, status: stage } : p));
      // Refresh timeline to show the stage change
      const timelineRes = await fetchClientTimeline(user.tenantId, leadId, token);
      setTimeline(timelineRes.timeline || []);
      setHasMore(timelineRes.has_more || false);
      setTimelineOffset(timelineRes.timeline?.length || 0);
    } catch (err) {
      console.error("Failed to change stage", err);
    }
  };

  const handleAddNote = async () => {
    if (!noteText.trim() || !user?.tenantId) return;
    setSaving(true);
    try {
      const note = await addClientNote(user.tenantId, leadId, token, noteText.trim());
      setProfile((p) => (p ? { ...p, client_notes: [note, ...p.client_notes] } : p));
      setNoteText("");
      // Refresh timeline
      const timelineRes = await fetchClientTimeline(user.tenantId, leadId, token);
      setTimeline(timelineRes.timeline || []);
      setHasMore(timelineRes.has_more || false);
      setTimelineOffset(timelineRes.timeline?.length || 0);
    } catch (err) {
      console.error("Failed to add note", err);
    } finally {
      setSaving(false);
    }
  };

  const handleLoadMore = async () => {
    if (!user?.tenantId) return;
    try {
      const res = await fetchClientTimeline(user.tenantId, leadId, token, {
        offset: timelineOffset,
      });
      setTimeline((prev) => [...prev, ...(res.timeline || [])]);
      setHasMore(res.has_more || false);
      setTimelineOffset((o) => o + (res.timeline?.length || 0));
    } catch (err) {
      console.error("Failed to load more timeline", err);
    }
  };

  const handleEditSave = async (field) => {
    if (!user?.tenantId) return;
    try {
      await updateClient(user.tenantId, leadId, token, { [field]: editValue });
      setProfile((p) => (p ? { ...p, [field]: editValue } : p));
      setEditing(null);
      setEditValue("");
    } catch (err) {
      console.error("Failed to update field", err);
    }
  };

  const startEdit = (field, currentValue) => {
    setEditing(field);
    setEditValue(currentValue || "");
  };

  const openSmsModal = () => {
    setSmsPhone(profile?.phone || "");
    setSmsMessage("");
    setSmsResult(null);
    setShowSmsModal(true);
  };

  const handleSendSms = async () => {
    if (!smsPhone.trim() || !smsMessage.trim() || !user?.tenantId) return;
    setSmsSending(true);
    setSmsResult(null);
    try {
      await sendSms(token, { lead_id: leadId, phone: smsPhone, message: smsMessage });
      setSmsResult("sent");
      // Refresh timeline
      const timelineRes = await fetchClientTimeline(user.tenantId, leadId, token);
      setTimeline(timelineRes.timeline || []);
      setHasMore(timelineRes.has_more || false);
      setTimelineOffset(timelineRes.timeline?.length || 0);
      setTimeout(() => setShowSmsModal(false), 1500);
    } catch (err) {
      console.error("Failed to send SMS", err);
      setSmsResult("error");
    } finally {
      setSmsSending(false);
    }
  };

  if (!leadId) {
    return (
      <div className="fade-in">
        <p>No client selected.</p>
        <button className="btn-sm" onClick={() => onNavigate("clients")}>Back to Clients</button>
      </div>
    );
  }

  if (loading) return <SkeletonLoader />;
  if (!profile) {
    return (
      <div className="fade-in">
        <p>Client not found.</p>
        <button className="btn-sm" onClick={() => onNavigate("clients")}>Back to Clients</button>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="profile-header">
        <button className="profile-back" onClick={() => onNavigate("clients")}>
          Back
        </button>
        <div className="profile-name">{profile.name || "Unknown"}</div>
        <span className={`score-badge ${scoreLabel(profile.lead_score)}`}>
          {profile.lead_score}
        </span>
        <select
          className="profile-stage-select"
          value={profile.status}
          onChange={(e) => handleStageChange(e.target.value)}
        >
          {STAGES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Body */}
      <div className="profile-body">
        {/* Timeline (main) */}
        <div className="timeline-section">
          <h3>Activity Timeline</h3>
          {timeline.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              No activity recorded yet.
            </p>
          ) : (
            <div className="timeline-list">
              {timeline.map((item) => (
                <div key={item.id} className={`timeline-item ${item.activity_type}`}>
                  <div className="timeline-desc">{item.description}</div>
                  <div className="timeline-time">{timeAgo(item.created_at)}</div>
                </div>
              ))}
            </div>
          )}
          {hasMore && (
            <button className="timeline-load-more" onClick={handleLoadMore}>
              Load more...
            </button>
          )}
        </div>

        {/* Sidebar */}
        <div className="profile-sidebar">
          {/* Contact Info */}
          <div className="sidebar-panel">
            <h4>Contact Info</h4>
            {["email", "phone"].map((field) => (
              <div key={field} className="sidebar-panel-row">
                <span className="sidebar-panel-label">{field.charAt(0).toUpperCase() + field.slice(1)}</span>
                {editing === field ? (
                  <span style={{ display: "flex", gap: "0.25rem" }}>
                    <input
                      style={{
                        background: "var(--bg-secondary)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius-sm)",
                        color: "var(--text-primary)",
                        padding: "0.2rem 0.4rem",
                        fontSize: "0.8rem",
                        width: "140px",
                      }}
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleEditSave(field)}
                      autoFocus
                    />
                    <button className="btn-sm" style={{ padding: "0.2rem 0.4rem" }} onClick={() => handleEditSave(field)}>OK</button>
                    <button className="btn-sm" style={{ padding: "0.2rem 0.4rem" }} onClick={() => setEditing(null)}>X</button>
                  </span>
                ) : (
                  <span
                    className="sidebar-panel-value editable"
                    onClick={() => startEdit(field, profile[field])}
                  >
                    {profile[field] || "Add..."}
                  </span>
                )}
              </div>
            ))}
            {profile.phone && (
              <div className="sidebar-panel-row">
                <button
                  className="btn-sm"
                  style={{ fontSize: "0.75rem", padding: "0.2rem 0.5rem" }}
                  onClick={openSmsModal}
                >
                  Send SMS
                </button>
              </div>
            )}
            {profile.areas_of_interest && (
              <div className="sidebar-panel-row">
                <span className="sidebar-panel-label">Interest</span>
                <span className="sidebar-panel-value">{profile.areas_of_interest}</span>
              </div>
            )}
            {profile.lead_temperature && (
              <div className="sidebar-panel-row">
                <span className="sidebar-panel-label">Temperature</span>
                <span className="sidebar-panel-value">{profile.lead_temperature}</span>
              </div>
            )}
          </div>

          {/* Lead Score */}
          <div className="sidebar-panel">
            <h4>Lead Score</h4>
            <div style={{ textAlign: "center", padding: "0.5rem 0" }}>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>
                {profile.lead_score}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                / 100 - {profile.lead_score >= 70 ? "Hot" : profile.lead_score >= 40 ? "Warm" : "Cold"}
              </div>
            </div>
          </div>

          {/* Notes */}
          <div className="sidebar-panel">
            <h4>Notes</h4>
            <div className="notes-input-group">
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Add a note..."
              />
              <button onClick={handleAddNote} disabled={saving || !noteText.trim()}>
                {saving ? "..." : "Add"}
              </button>
            </div>
            {profile.client_notes.length === 0 && !profile.conversation_summary ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>No notes yet.</p>
            ) : (
              <>
                {profile.client_notes.map((n) => (
                  <div key={n.id} className="note-item">
                    <div className="note-content">{n.content}</div>
                    <div className="note-time">{timeAgo(n.created_at)}</div>
                  </div>
                ))}
                {profile.conversation_summary && (
                  <div className="note-item">
                    <div className="note-content">{profile.conversation_summary}</div>
                    <div className="note-time">Conversation summary</div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Conversations */}
          <div className="sidebar-panel">
            <h4>Conversations</h4>
            {profile.conversations.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>No conversations.</p>
            ) : (
              profile.conversations.map((c) => (
                <div key={c.id} className="conv-summary">
                  {c.message_count} message{c.message_count !== 1 ? "s" : ""}
                  {c.last_message_at ? ` - ${timeAgo(c.last_message_at)}` : ""}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* SMS Modal */}
      {showSmsModal && (
        <div
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
          }}
          onClick={(e) => e.target === e.currentTarget && setShowSmsModal(false)}
        >
          <div style={{
            background: "var(--bg-card)", border: "1px solid var(--border)",
            borderRadius: "var(--radius)", width: "440px", padding: "24px",
            display: "flex", flexDirection: "column", gap: "16px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, color: "var(--text-primary)" }}>Send SMS</h3>
              <button
                onClick={() => setShowSmsModal(false)}
                style={{ background: "none", border: "none", color: "var(--text-secondary)", cursor: "pointer", fontSize: "18px" }}
              >&times;</button>
            </div>
            <div>
              <label style={{ color: "var(--text-secondary)", fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "4px" }}>Phone</label>
              <input
                value={smsPhone}
                onChange={(e) => setSmsPhone(e.target.value)}
                style={{
                  width: "100%", padding: "8px 10px", background: "var(--bg-primary)",
                  border: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)", fontSize: "14px", boxSizing: "border-box",
                }}
              />
            </div>
            <div>
              <label style={{ color: "var(--text-secondary)", fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "4px" }}>
                Message ({1600 - smsMessage.length} chars remaining)
              </label>
              <textarea
                value={smsMessage}
                onChange={(e) => setSmsMessage(e.target.value.slice(0, 1600))}
                maxLength={1600}
                rows={5}
                style={{
                  width: "100%", padding: "8px 10px", background: "var(--bg-primary)",
                  border: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)", fontSize: "14px", resize: "vertical",
                  fontFamily: "inherit", boxSizing: "border-box",
                }}
                placeholder="Type your message..."
              />
            </div>
            {smsResult === "sent" && (
              <div style={{ color: "var(--green, #22c55e)", fontSize: "13px" }}>SMS sent successfully!</div>
            )}
            {smsResult === "error" && (
              <div style={{ color: "var(--red, #ef4444)", fontSize: "13px" }}>Failed to send SMS. Please try again.</div>
            )}
            <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowSmsModal(false)}
                style={{
                  padding: "8px 14px", background: "transparent", color: "var(--text-secondary)",
                  border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", cursor: "pointer",
                }}
              >Cancel</button>
              <button
                onClick={handleSendSms}
                disabled={smsSending || !smsPhone.trim() || !smsMessage.trim()}
                className="btn-primary"
                style={{ padding: "8px 16px", opacity: smsSending || !smsPhone.trim() || !smsMessage.trim() ? 0.5 : 1 }}
              >
                {smsSending ? "Sending..." : "Send SMS"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
