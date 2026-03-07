import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { validateInvite, acceptInvite } from "../utils/api";

export default function AcceptInvitePage() {
  const { token: inviteToken } = useParams();
  const navigate = useNavigate();
  const [invite, setInvite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await validateInvite(inviteToken);
        setInvite(data);
      } catch (err) {
        setError(err.body?.detail || "Invalid or expired invitation link");
      } finally {
        setLoading(false);
      }
    })();
  }, [inviteToken]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setSubmitting(true);
    try {
      const result = await acceptInvite(inviteToken, { name, password });
      localStorage.setItem("anx_token", result.token);
      localStorage.setItem("anx_tenant_id", result.tenant_id);
      navigate("/dashboard");
      window.location.reload();
    } catch (err) {
      setError(err.body?.detail || "Failed to accept invitation");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="invite-page">
        <div className="invite-card">
          <p>Validating invitation...</p>
        </div>
      </div>
    );
  }

  if (!invite) {
    return (
      <div className="invite-page">
        <div className="invite-card">
          <h1>Invalid Invitation</h1>
          <p className="invite-error">{error}</p>
          <a href="/signup" className="btn-primary" style={{ display: "inline-block", marginTop: 16 }}>
            Sign up instead
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="invite-page">
      <div className="invite-card">
        <div className="invite-logo">AgentNexLiFy</div>
        <h1>Join {invite.business_name}</h1>
        <p className="invite-subtitle">
          You've been invited as <strong>{invite.role}</strong> to <strong>{invite.business_name}</strong>
        </p>
        <p className="invite-email">{invite.email}</p>

        {error && <div className="invite-error">{error}</div>}

        <form onSubmit={handleSubmit} className="invite-form">
          <div className="invite-field">
            <label>Your Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your full name"
              required
            />
          </div>
          <div className="invite-field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
              minLength={8}
            />
          </div>
          <div className="invite-field">
            <label>Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm password"
              required
            />
          </div>
          <button type="submit" className="btn-primary invite-submit" disabled={submitting}>
            {submitting ? "Setting up..." : "Accept & Join"}
          </button>
        </form>
      </div>
    </div>
  );
}
