import { useState } from "react";
import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { submitPartnerInquiry } from "../utils/api/dashboard";
import "../styles/legal.css";
import "../styles/contact.css";

const TIERS = [
  { seats: "1-4 client accounts", price: "$99.99/mo per seat", note: "Retail" },
  { seats: "5-14 client accounts", price: "$79.99/mo per seat", note: "20% off" },
  { seats: "15+ client accounts", price: "$69.99/mo per seat", note: "30% off" },
];

export default function Partners() {
  const [form, setForm] = useState({
    agency_name: "",
    contact_name: "",
    email: "",
    client_count: "",
    message: "",
    website: "", // honeypot: hidden from real users
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await submitPartnerInquiry(form);
      setSuccess(true);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="legal-page">
      <Helmet>
        <title>Agency &amp; Reseller Program | AgentNexLiFy</title>
        <meta
          name="description"
          content="White-label AgentNexLiFy's AI front desk for your clients. Volume pricing from $69.99/seat, your branding, 13 industry knowledge packs."
        />
        <link rel="canonical" href="https://agentnexlify.com/partners" />
      </Helmet>

      <nav className="legal-nav">
        <Link to="/" className="legal-back">
          &larr; Back to Home
        </Link>
        <Link to="/pricing" className="legal-sibling">
          Pricing
        </Link>
      </nav>

      <article className="legal-content">
        <h1>Agency &amp; Reseller Program</h1>

        <p className="contact-intro">
          Add an AI front desk to every client you manage, white-labeled as
          yours. You bill your clients at your retail price; your cost is the
          partner rate below.
        </p>

        <div
          style={{
            marginBottom: "2rem",
            borderRadius: 10,
            border: "1px solid var(--border-color, #e2e8f0)",
            overflow: "hidden",
          }}
        >
          {TIERS.map((tier, i) => (
            <div
              key={tier.seats}
              style={{
                display: "flex",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "0.5rem",
                padding: "0.9rem 1.25rem",
                borderTop: i === 0 ? "none" : "1px solid var(--border-color, #e2e8f0)",
                background: i === 2 ? "rgba(59,130,246,0.08)" : "transparent",
              }}
            >
              <span>{tier.seats}</span>
              <span>
                <strong>{tier.price}</strong>
                <span style={{ color: "var(--text-secondary, #475569)", marginLeft: 8 }}>
                  {tier.note}
                </span>
              </span>
            </div>
          ))}
        </div>

        <ul style={{ marginBottom: "2rem" }}>
          <li>Your branding on the widget and dashboard (white-label included).</li>
          <li>13 industry knowledge packs: client setup takes minutes, not days.</li>
          <li>Lead capture, appointment booking, and follow-up automation per client.</li>
          <li>Month-to-month. No certification fee, no minimum term.</li>
        </ul>

        {success ? (
          <div
            style={{
              padding: "1.25rem",
              borderRadius: 10,
              background: "rgba(34,197,94,0.1)",
              border: "1px solid rgba(34,197,94,0.25)",
            }}
          >
            <strong>Inquiry received.</strong> We reply within one business day
            with partner onboarding details.
          </div>
        ) : (
          <form className="contact-form" onSubmit={handleSubmit}>
            <label>
              Agency name
              <input
                name="agency_name"
                value={form.agency_name}
                onChange={handleChange}
                required
                minLength={2}
                maxLength={200}
              />
            </label>
            <label>
              Your name
              <input
                name="contact_name"
                value={form.contact_name}
                onChange={handleChange}
                required
                minLength={2}
                maxLength={200}
              />
            </label>
            <label>
              Email
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                required
              />
            </label>
            <label>
              How many clients do you manage?
              <input
                name="client_count"
                value={form.client_count}
                onChange={handleChange}
                maxLength={50}
                placeholder="e.g. 12"
              />
            </label>
            <label>
              Anything else?
              <textarea
                name="message"
                value={form.message}
                onChange={handleChange}
                maxLength={2000}
                rows={4}
              />
            </label>
            {/* Honeypot field: hidden from humans, bots fill it */}
            <input
              name="website"
              value={form.website}
              onChange={handleChange}
              tabIndex={-1}
              autoComplete="off"
              aria-hidden="true"
              style={{ position: "absolute", left: "-9999px", height: 0, width: 0, opacity: 0 }}
            />
            {error && (
              <p style={{ color: "var(--red, #dc2626)" }}>{error}</p>
            )}
            <button type="submit" className="contact-submit" disabled={loading}>
              {loading ? "Sending..." : "Apply to the partner program"}
            </button>
          </form>
        )}
      </article>
    </div>
  );
}
