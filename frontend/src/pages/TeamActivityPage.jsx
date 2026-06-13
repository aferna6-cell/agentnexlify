import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchTeamActivity, fetchTeamMembers } from "../utils/api/team";
import SkeletonLoader from "../components/SkeletonLoader";

const ACTIVITY_ICONS = {
  lead_created: { emoji: "+", color: "#10b981" },
  assignment: { emoji: "=", color: "#6366f1" },
  email_sent: { emoji: "@", color: "#3b82f6" },
  sms_sent: { emoji: "#", color: "#22c55e" },
  lead_merged: { emoji: "M", color: "#f59e0b" },
  team_reply: { emoji: ">", color: "#8b5cf6" },
  stage_change: { emoji: "~", color: "#ec4899" },
};

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function TeamActivityPage() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [activity, setActivity] = useState([]);
  const [members, setMembers] = useState([]);
  const [selectedMember, setSelectedMember] = useState("");
  const [days, setDays] = useState(7);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const [actRes, memRes] = await Promise.allSettled([
        fetchTeamActivity(user.tenantId, token, { memberId: selectedMember || undefined, days }),
        fetchTeamMembers(user.tenantId, token),
      ]);
      if (actRes.status === "fulfilled") setActivity(actRes.value.activity || []);
      if (memRes.status === "fulfilled") setMembers(memRes.value.members || memRes.value || []);
    } catch (err) {
      console.error("Failed to load team activity:", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, selectedMember, days]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Team Activity</h1>
        <p>Track what your team members are doing</p>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <select
          value={selectedMember}
          onChange={(e) => setSelectedMember(e.target.value)}
          style={{
            padding: "8px 12px", borderRadius: 8,
            background: "var(--bg-secondary)", color: "var(--text-primary)",
            border: "1px solid var(--border)", fontSize: "0.85rem",
          }}
        >
          <option value="">All Team Members</option>
          {(Array.isArray(members) ? members : []).map((m) => (
            <option key={m.id} value={m.id}>{m.name || m.email}</option>
          ))}
        </select>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          style={{
            padding: "8px 12px", borderRadius: 8,
            background: "var(--bg-secondary)", color: "var(--text-primary)",
            border: "1px solid var(--border)", fontSize: "0.85rem",
          }}
        >
          <option value={1}>Last 24 hours</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
        </select>
      </div>

      {activity.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem 1rem" }}>
          <p style={{ color: "var(--text-muted)", fontSize: "1rem" }}>
            No team activity recorded yet. Activity is logged when team members create leads, assign them, send emails/SMS, or reply to conversations.
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div style={{
            display: "grid", gridTemplateColumns: "auto 1fr auto",
            gap: 0, fontSize: "0.85rem",
          }}>
            <div style={{ display: "contents" }}>
              <div style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid var(--border)", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.5px" }}>Who</div>
              <div style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid var(--border)", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.5px" }}>Action</div>
              <div style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid var(--border)", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.5px", textAlign: "right" }}>When</div>
            </div>
            {activity.map((a) => {
              const config = ACTIVITY_ICONS[a.activity_type] || { emoji: ".", color: "#666" };
              return (
                <div key={a.id} style={{ display: "contents" }}>
                  <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{
                      width: 28, height: 28, borderRadius: "50%",
                      background: `${config.color}20`, color: config.color,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "0.75rem", fontWeight: 700, flexShrink: 0,
                    }}>
                      {(a.performed_by_name || "?")[0].toUpperCase()}
                    </span>
                    <span style={{ fontWeight: 500 }}>{a.performed_by_name || "Unknown"}</span>
                  </div>
                  <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", color: "var(--text-primary)" }}>
                    <span style={{
                      display: "inline-block", padding: "2px 8px", borderRadius: 4,
                      background: `${config.color}15`, color: config.color,
                      fontSize: "0.7rem", fontWeight: 600, marginRight: 8,
                      textTransform: "uppercase",
                    }}>
                      {a.activity_type.replace(/_/g, " ")}
                    </span>
                    {a.description}
                  </div>
                  <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", color: "var(--text-muted)", textAlign: "right", whiteSpace: "nowrap" }}>
                    {timeAgo(a.created_at)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
