import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { submitSupportContact } from "../utils/api/support";

const SUBJECTS = [
  "General question",
  "Billing or subscription",
  "Widget setup help",
  "Bug report",
  "Feature request",
  "Account access",
  "Other",
];

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function SupportPage() {
  const { user, token } = useAuth();

  const [form, setForm] = useState({
    name: user?.name || user?.businessName || "",
    email: user?.email || "",
    subject: "",
    message: "",
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [submitError, setSubmitError] = useState("");

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }
  }

  function validate() {
    const next = {};
    if (!form.name.trim()) next.name = "Name is required.";
    if (!form.email.trim()) {
      next.email = "Email is required.";
    } else if (!isValidEmail(form.email.trim())) {
      next.email = "Enter a valid email address.";
    }
    if (!form.subject) next.subject = "Please select a subject.";
    if (!form.message.trim()) next.message = "Message is required.";
    return next;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitError("");

    const fieldErrors = validate();
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors);
      return;
    }

    setLoading(true);
    try {
      await submitSupportContact(
        {
          name: form.name.trim(),
          email: form.email.trim(),
          subject: form.subject,
          message: form.message.trim(),
        },
        token,
      );
      setSent(true);
    } catch (err) {
      const msg =
        err?.body?.detail ||
        err?.message ||
        "Something went wrong. Please try again.";
      setSubmitError(msg);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setSent(false);
    setForm((prev) => ({ ...prev, subject: "", message: "" }));
    setErrors({});
    setSubmitError("");
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Support</h1>
        <p>Get help from the AgentNexLiFy team. We typically respond within one business day.</p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <div className="settings-card">
          <h3 style={{ marginBottom: "0.5rem" }}>Response Time</h3>
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>Within one business day.</p>
        </div>
        <div className="settings-card">
          <h3 style={{ marginBottom: "0.5rem" }}>Business Hours</h3>
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>Mon - Fri, 9 AM - 6 PM EST</p>
        </div>
        <div className="settings-card">
          <h3 style={{ marginBottom: "0.5rem" }}>Helpful to include</h3>
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>Steps to reproduce, screenshots, and your plan tier.</p>
        </div>
      </div>

      <div className="settings-card">
        <h3>Send a Message</h3>

        {sent ? (
          <div
            style={{ padding: "1.5rem", textAlign: "center" }}
            data-testid="success-state"
          >
            <p
              style={{
                fontSize: "1.1rem",
                marginBottom: "0.5rem",
                color: "var(--text-primary)",
              }}
            >
              Thanks - we'll get back to you within one business day.
            </p>
            <p style={{ color: "var(--text-secondary)", marginBottom: "1rem" }}>
              Check your inbox for a confirmation.
            </p>
            <button className="btn-primary" onClick={handleReset}>
              Send Another Message
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            <div className="settings-field">
              <label htmlFor="support-name">Name</label>
              <input
                id="support-name"
                type="text"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="Your name"
                autoComplete="name"
              />
              {errors.name && (
                <span
                  style={{ color: "var(--red)", fontSize: "0.85rem" }}
                  data-testid="error-name"
                >
                  {errors.name}
                </span>
              )}
            </div>

            <div className="settings-field">
              <label htmlFor="support-email">Email</label>
              <input
                id="support-email"
                type="email"
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
              {errors.email && (
                <span
                  style={{ color: "var(--red)", fontSize: "0.85rem" }}
                  data-testid="error-email"
                >
                  {errors.email}
                </span>
              )}
            </div>

            <div className="settings-field">
              <label htmlFor="support-subject">Subject</label>
              <select
                id="support-subject"
                value={form.subject}
                onChange={(e) => set("subject", e.target.value)}
              >
                <option value="">Select a topic...</option>
                {SUBJECTS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              {errors.subject && (
                <span
                  style={{ color: "var(--red)", fontSize: "0.85rem" }}
                  data-testid="error-subject"
                >
                  {errors.subject}
                </span>
              )}
            </div>

            <div className="settings-field">
              <label htmlFor="support-message">Message</label>
              <textarea
                id="support-message"
                value={form.message}
                onChange={(e) => set("message", e.target.value)}
                rows={6}
                placeholder="Describe your issue or question in detail..."
              />
              {errors.message && (
                <span
                  style={{ color: "var(--red)", fontSize: "0.85rem" }}
                  data-testid="error-message"
                >
                  {errors.message}
                </span>
              )}
            </div>

            {submitError && (
              <div
                style={{
                  color: "var(--red)",
                  marginBottom: "0.75rem",
                  padding: "0.5rem",
                  background: "rgba(239, 68, 68, 0.08)",
                  borderRadius: "4px",
                }}
                data-testid="submit-error"
              >
                {submitError}
              </div>
            )}

            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
              data-testid="submit-btn"
            >
              {loading ? "Sending..." : "Send Message"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
