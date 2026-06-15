import { useState } from "react";
import { useAuth } from "../context/AuthContext";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

export default function SupportPage() {
  const { user, token } = useAuth();
  const [form, setForm] = useState({
    name: user?.name || user?.businessName || "",
    email: user?.email || "",
    message: "",
  });
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/support/contact`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error("Failed to send");
      setSent(true);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Support</h1>
        <p>Get help from the AgentNexLiFy team</p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <div className="settings-card">
          <h3 style={{ marginBottom: "0.5rem" }}>Email Us</h3>
          <a
            href="mailto:help@agentnexlify.com"
            style={{ color: "var(--accent)" }}
          >
            help@agentnexlify.com
          </a>
        </div>
        <div className="settings-card">
          <h3 style={{ marginBottom: "0.5rem" }}>Response Time</h3>
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>
            We typically respond within 24 hours
          </p>
        </div>
        <div className="settings-card">
          <h3 style={{ marginBottom: "0.5rem" }}>Business Hours</h3>
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>
            Monday - Friday, 9 AM - 6 PM EST
          </p>
        </div>
      </div>

      <div className="settings-card">
        <h3>Send a Message</h3>
        {sent ? (
          <div style={{ padding: "1.5rem", textAlign: "center" }}>
            <p style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>
              Message sent!
            </p>
            <p style={{ color: "var(--text-secondary)" }}>
              We'll get back to you within 24 hours.
            </p>
            <button
              className="btn-primary"
              onClick={() => {
                setSent(false);
                setForm((f) => ({ ...f, message: "" }));
              }}
              style={{ marginTop: "1rem" }}
            >
              Send Another
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="settings-field">
              <label>Name</label>
              <input
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
                required
              />
            </div>
            <div className="settings-field">
              <label>Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) =>
                  setForm((f) => ({ ...f, email: e.target.value }))
                }
                required
              />
            </div>
            <div className="settings-field">
              <label>How can we help?</label>
              <textarea
                value={form.message}
                onChange={(e) =>
                  setForm((f) => ({ ...f, message: e.target.value }))
                }
                rows={5}
                required
                placeholder="Describe your issue or question..."
              />
            </div>
            {error && (
              <div style={{ color: "var(--red)", marginBottom: "0.75rem" }}>
                {error}
              </div>
            )}
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Sending..." : "Send Message"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
