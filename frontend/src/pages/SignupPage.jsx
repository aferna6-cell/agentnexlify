import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { trackEvent } from "../utils/analytics";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://agentnexlify-production.up.railway.app";
const PAID_PLANS = new Set(["growth", "professional", "enterprise"]);

const INDUSTRIES = [
  { value: "accounting", label: "Accounting" },
  { value: "auto_shop", label: "Auto Shop" },
  { value: "bakery", label: "Bakery" },
  { value: "bar_nightclub", label: "Bar / Nightclub" },
  { value: "cafe", label: "Café / Coffee Shop" },
  { value: "catering", label: "Catering" },
  { value: "chiropractic", label: "Chiropractic" },
  { value: "cleaning", label: "Cleaning Services" },
  { value: "dental", label: "Dental" },
  { value: "electrical", label: "Electrical" },
  { value: "fitness", label: "Fitness" },
  { value: "food_truck", label: "Food Truck" },
  { value: "hvac", label: "HVAC" },
  { value: "landscaping", label: "Landscaping" },
  { value: "legal", label: "Legal" },
  { value: "medical", label: "Medical" },
  { value: "moving", label: "Moving" },
  { value: "pest_control", label: "Pest Control" },
  { value: "photography", label: "Photography" },
  { value: "plumbing", label: "Plumbing" },
  { value: "realestate", label: "Real Estate" },
  { value: "restaurant", label: "Restaurant" },
  { value: "roofing", label: "Roofing" },
  { value: "salon", label: "Salon" },
  { value: "tutoring", label: "Tutoring" },
  { value: "veterinary", label: "Veterinary" },
  { value: "other", label: "Other" },
];

export default function SignupPage() {
  const [searchParams] = useSearchParams();
  const requestedPlan = (searchParams.get("plan") || "").toLowerCase();
  const checkoutPlan = PAID_PLANS.has(requestedPlan) ? requestedPlan : "";
  const googleSetupToken = searchParams.get("google_setup") || "";
  const googleEmail = searchParams.get("email") || "";
  const googleName = searchParams.get("name") || "";
  const googleError = searchParams.get("google_error") || "";
  const isGoogleSignup = Boolean(googleSetupToken);
  const [form, setForm] = useState(() => ({
    business_name: "",
    owner_name: googleName,
    email: googleEmail,
    phone: "",
    website_url: "",
    industry: "other",
    city: "",
    password: "",
    confirmPassword: "",
  }));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => {
    if (googleError) {
      setError("Google sign-up could not be completed. Please try again.");
    }
  }, [googleError]);

  useEffect(() => {
    if (!isGoogleSignup) return;
    setForm((current) => ({
      ...current,
      owner_name: googleName || current.owner_name,
      email: googleEmail || current.email,
    }));
  }, [googleEmail, googleName, isGoogleSignup]);

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!isGoogleSignup && form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      const endpoint = isGoogleSignup
        ? `${API_BASE}/api/v1/auth/google-register`
        : `${API_BASE}/api/v1/auth/register`;
      const body = isGoogleSignup
        ? {
            setup_token: googleSetupToken,
            business_name: form.business_name,
            phone: form.phone || undefined,
            website_url: form.website_url || undefined,
            industry: form.industry,
            city: form.city,
          }
        : {
            business_name: form.business_name,
            owner_name: form.owner_name,
            email: form.email,
            phone: form.phone || undefined,
            website_url: form.website_url || undefined,
            industry: form.industry,
            city: form.city,
            password: form.password,
          };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Registration failed");
      }

      const { token, tenant_id } = await res.json();
      localStorage.setItem("anx_token", token);
      localStorage.setItem("anx_tenant_id", tenant_id);
      trackEvent("sign_up", { method: isGoogleSignup ? "google" : "email", plan: checkoutPlan || "free" });

      if (checkoutPlan) {
        const checkoutRes = await fetch(`${API_BASE}/api/v1/auth/billing/checkout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ plan: checkoutPlan }),
        });

        const checkoutData = await checkoutRes.json().catch(() => ({}));
        if (checkoutRes.ok && checkoutData.checkout_url) {
          trackEvent("begin_checkout", { event_label: "signup_redirect", plan: checkoutPlan });
          window.location.href = checkoutData.checkout_url;
          return;
        }
      }

      window.location.href = "/dashboard";
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSignup() {
    setError("");
    setGoogleLoading(true);
    try {
      const params = new URLSearchParams({ mode: "signup" });
      if (checkoutPlan) params.set("plan", checkoutPlan);

      const res = await fetch(`${API_BASE}/api/v1/auth/google/url?${params.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.auth_url) {
        throw new Error(data.detail || "Google sign-up is not available yet");
      }
      window.location.href = data.auth_url;
    } catch (err) {
      setError(err.message);
      setGoogleLoading(false);
    }
  }

  const submitLabel = loading
    ? isGoogleSignup
      ? "Finishing setup..."
      : "Creating account..."
    : checkoutPlan
      ? `Continue to ${checkoutPlan[0].toUpperCase()}${checkoutPlan.slice(1)} checkout`
      : isGoogleSignup
        ? "Finish Google Signup"
        : "Get Started Free";

  return (
    <div className="login-page">
      <div className="login-card" style={{ width: 420 }}>
        <h1 className="login-title">AgentNexLiFy</h1>
        <p className="login-subtitle">
          {checkoutPlan
            ? `Create your account to continue with the ${checkoutPlan[0].toUpperCase()}${checkoutPlan.slice(1)} plan`
            : "Create your free account"}
        </p>
        {!isGoogleSignup ? (
          <>
            <button
              type="button"
              className="login-btn"
              onClick={handleGoogleSignup}
              disabled={loading || googleLoading}
              style={{ marginBottom: "1rem", background: "#fff", color: "#111827", border: "1px solid rgba(255,255,255,0.18)" }}
            >
              {googleLoading ? "Redirecting to Google..." : "Sign up with Google"}
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
              <span style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
              <span>or continue with email</span>
              <span style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
            </div>
          </>
        ) : (
          <div style={{ marginBottom: "1rem", padding: "0.875rem 1rem", borderRadius: 12, background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.25)", color: "var(--text-secondary)" }}>
            Using Google account <strong style={{ color: "var(--text-primary)" }}>{googleEmail}</strong>. Finish your business setup below.
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="login-field">
            <label>Business Name</label>
            <input
              className="login-input"
              value={form.business_name}
              onChange={update("business_name")}
              placeholder="Acme Plumbing"
              required
            />
          </div>
          <div className="login-field">
            <label>Your Name</label>
            <input
              className="login-input"
              value={form.owner_name}
              onChange={update("owner_name")}
              placeholder="Jane Smith"
              required
              readOnly={isGoogleSignup}
            />
          </div>
          <div className="login-field">
            <label>Email</label>
            <input
              type="email"
              className="login-input"
              value={form.email}
              onChange={update("email")}
              placeholder="you@company.com"
              required
              readOnly={isGoogleSignup}
            />
          </div>
          <div className="login-field">
            <label>Phone <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(optional)</span></label>
            <input
              type="tel"
              className="login-input"
              value={form.phone}
              onChange={update("phone")}
              placeholder="(555) 123-4567"
            />
          </div>
          <div className="login-field">
            <label>Website <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(optional)</span></label>
            <input
              type="url"
              className="login-input"
              value={form.website_url}
              onChange={update("website_url")}
              placeholder="https://yoursite.com"
            />
          </div>
          <div className="login-field">
            <label>Industry</label>
            <select
              className="login-input"
              value={form.industry}
              onChange={update("industry")}
            >
              {INDUSTRIES.map((i) => (
                <option key={i.value} value={i.value}>
                  {i.label}
                </option>
              ))}
            </select>
          </div>
          <div className="login-field">
            <label>City</label>
            <input
              className="login-input"
              value={form.city}
              onChange={update("city")}
              placeholder="New York"
            />
          </div>
          {!isGoogleSignup && (
            <>
              <div className="login-field">
                <label>Password</label>
                <input
                  type="password"
                  className="login-input"
                  value={form.password}
                  onChange={update("password")}
                  placeholder="Min. 8 characters"
                  minLength={8}
                  required
                />
              </div>
              <div className="login-field">
                <label>Confirm Password</label>
                <input
                  type="password"
                  className="login-input"
                  value={form.confirmPassword}
                  onChange={update("confirmPassword")}
                  placeholder="Re-enter password"
                  required
                />
              </div>
            </>
          )}
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="login-btn" disabled={loading || googleLoading}>
            {submitLabel}
          </button>
          <p className="login-legal-note">
            By signing up, you agree to our{" "}
            <Link to="/terms">Terms of Service</Link> and{" "}
            <Link to="/privacy">Privacy Policy</Link>.
          </p>
        </form>
        <p className="login-footer">
          Already have an account?{" "}
          <Link to="/login" className="login-link">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
