import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchTeamMembers,
  inviteTeamMember,
  updateTeamMemberRole,
  removeTeamMember,
  resendInvite,
} from "../utils/api/team";

const roleOptions = [
  { value: "admin", label: "Admin", desc: "Can manage team & settings" },
  { value: "member", label: "Member", desc: "Full access to data" },
  { value: "viewer", label: "Viewer", desc: "Read-only access" },
];

const roleBadgeStyles = {
  owner: { color: "var(--yellow)", background: "var(--yellow-dim)" },
  admin: { color: "var(--purple)", background: "var(--purple-dim)" },
  member: { color: "var(--accent)", background: "var(--accent-dim)" },
  viewer: { color: "var(--text-secondary)", background: "var(--hover-overlay)" },
};

export default function TeamPage() {
  const { token, user } = useAuth();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadMembers = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const data = await fetchTeamMembers(user.tenantId, token);
      setMembers(data);
    } catch (err) {
      setError("Failed to load team members");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const handleInvite = async (e) => {
    e.preventDefault();
    setInviting(true);
    setError("");
    setSuccess("");
    try {
      await inviteTeamMember(user.tenantId, token, {
        email: inviteEmail,
        role: inviteRole,
        name: inviteName || null,
      });
      setSuccess(`Invitation sent to ${inviteEmail}`);
      setInviteEmail("");
      setInviteName("");
      setInviteRole("member");
      setShowInvite(false);
      loadMembers();
    } catch (err) {
      setError(err.body?.detail || "Failed to send invite");
    } finally {
      setInviting(false);
    }
  };

  const handleRoleChange = async (memberId, newRole) => {
    setError("");
    try {
      await updateTeamMemberRole(user.tenantId, token, memberId, newRole);
      loadMembers();
    } catch (err) {
      setError(err.body?.detail || "Failed to update role");
    }
  };

  const handleRemove = async (memberId, email) => {
    if (!confirm(`Remove ${email} from the team?`)) return;
    setError("");
    try {
      await removeTeamMember(user.tenantId, token, memberId);
      setSuccess(`${email} has been removed`);
      loadMembers();
    } catch (err) {
      setError(err.body?.detail || "Failed to remove member");
    }
  };

  const handleResend = async (memberId, email) => {
    setError("");
    try {
      await resendInvite(user.tenantId, token, memberId);
      setSuccess(`Invite resent to ${email}`);
    } catch (err) {
      setError(err.body?.detail || "Failed to resend invite");
    }
  };

  const isOwner = user?.role === "owner";

  if (!user) return null;

  return (
    <div className="team-page">
      <div className="team-header">
        <div>
          <h1>Team Members</h1>
          <p className="team-subtitle">Manage who has access to your dashboard</p>
        </div>
        <button className="btn-primary" onClick={() => setShowInvite(true)}>
          + Invite Member
        </button>
      </div>

      {error && <div className="team-alert team-alert-error">{error}</div>}
      {success && <div className="team-alert team-alert-success">{success}</div>}

      {showInvite && (
        <div className="team-invite-modal-overlay" onClick={() => setShowInvite(false)}>
          <div className="team-invite-modal" onClick={(e) => e.stopPropagation()}>
            <h2>Invite Team Member</h2>
            <form onSubmit={handleInvite}>
              <div className="team-form-group">
                <label>Email *</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="team@example.com"
                  required
                />
              </div>
              <div className="team-form-group">
                <label>Name (optional)</label>
                <input
                  type="text"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  placeholder="John Doe"
                />
              </div>
              <div className="team-form-group">
                <label>Role</label>
                <div className="team-role-options">
                  {roleOptions.map((opt) => (
                    <label
                      key={opt.value}
                      className={`team-role-option${inviteRole === opt.value ? " selected" : ""}`}
                    >
                      <input
                        type="radio"
                        name="role"
                        value={opt.value}
                        checked={inviteRole === opt.value}
                        onChange={(e) => setInviteRole(e.target.value)}
                      />
                      <div>
                        <strong>{opt.label}</strong>
                        <span>{opt.desc}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
              <div className="team-modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowInvite(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={inviting}>
                  {inviting ? "Sending..." : "Send Invite"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="team-loading">Loading team...</div>
      ) : (
        <div className="team-table-wrapper">
          <table className="team-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id}>
                  <td>
                    <div className="team-member-info">
                      <div className="team-member-avatar">
                        {(m.name || m.email)[0].toUpperCase()}
                      </div>
                      <div>
                        <div className="team-member-name">{m.name || "-"}</div>
                        <div className="team-member-email">{m.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="team-role-badge" style={roleBadgeStyles[m.role]}>
                      {m.role}
                    </span>
                  </td>
                  <td>
                    <span className={`team-status ${m.invite_accepted ? "active" : "pending"}`}>
                      {m.invite_accepted ? "Active" : "Pending"}
                    </span>
                  </td>
                  <td className="team-last-login">
                    {m.last_login
                      ? new Date(m.last_login).toLocaleDateString()
                      : "-"}
                  </td>
                  <td>
                    {m.role !== "owner" && (
                      <div className="team-actions">
                        {isOwner && (
                          <select
                            value={m.role}
                            onChange={(e) => handleRoleChange(m.id, e.target.value)}
                            className="team-role-select"
                          >
                            <option value="admin">Admin</option>
                            <option value="member">Member</option>
                            <option value="viewer">Viewer</option>
                          </select>
                        )}
                        {!m.invite_accepted && (
                          <button
                            className="btn-ghost"
                            onClick={() => handleResend(m.id, m.email)}
                          >
                            Resend
                          </button>
                        )}
                        <button
                          className="btn-ghost btn-danger"
                          onClick={() => handleRemove(m.id, m.email)}
                        >
                          Remove
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
