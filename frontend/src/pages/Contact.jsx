import { useState } from "react";
import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { submitContactForm } from "../utils/api";
import "../styles/legal.css";
import "../styles/contact.css";

export default function Contact() {
  const [form, setForm] = useState({ name: "", email: "", message: "" });
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
      await submitContactForm(form);
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
        <title>Contact Us | AgentNexLiFy</title>
        <meta
          name="description"
          content="Get in touch with the AgentNexLiFy team. We'd love to hear from you."
        />
        <link rel="canonical" href="https://agentnexlify.com/contact" />
      </Helmet>

      <nav className="legal-nav">
        <Link to="/" className="legal-back">&larr; Back to Home</Link>
        <Link to="/terms" className="legal-sibling">Terms of Service</Link>
      </nav>

      <article className="legal-content">
        <h1>Get in Touch</h1>

        <p className="contact-intro">
          Have a question, feedback, or need help? Fill out the form below and
          we'll get back to you as soon as possible. You can also email us
          directly at{" "}
          <a href="mailto:support@agentnexlify.com">support@agentnexlify.com</a>.
        </p>

        {success ? (
          <div className="contact-success">
            Thanks for reaching out! We'll get back to you soon.
          </div>
        ) : (
          <form className="contact-form" onSubmit={handleSubmit}>
            <div className="contact-field">
              <label htmlFor="contact-name">Name</label>
              <input
                id="contact-name"
                name="name"
                type="text"
                placeholder="Your name"
                required
                value={form.name}
                onChange={handleChange}
              />
            </div>

            <div className="contact-field">
              <label htmlFor="contact-email">Email</label>
              <input
                id="contact-email"
                name="email"
                type="email"
                placeholder="you@example.com"
                required
                value={form.email}
                onChange={handleChange}
              />
            </div>

            <div className="contact-field">
              <label htmlFor="contact-message">Message</label>
              <textarea
                id="contact-message"
                name="message"
                placeholder="How can we help?"
                required
                value={form.message}
                onChange={handleChange}
              />
            </div>

            {error && <div className="contact-error">{error}</div>}

            <button type="submit" className="contact-submit" disabled={loading}>
              {loading ? "Sending..." : "Send Message"}
            </button>
          </form>
        )}
      </article>
    </div>
  );
}
