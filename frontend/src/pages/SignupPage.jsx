import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { trackEvent } from "../utils/analytics";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://agentnexlify-production.up.railway.app";
const PAID_PLANS = new Set(["growth", "autopilot", "professional", "enterprise"]);

// 4 fields and you're in. Industry, website, city, and phone moved into the
// /setup flow (express or wizard) — asking them twice killed the old funnel.
export default function SignupPage() {
  const [searchParams] = useSearchParams();
  const requestedPlan = (searchParams.get("plan") || "").toLowerCase();
  const checkoutPlan = PAID_PLANS.has(requestedPlan) ? requestedPlan : "";
  const googleSetupToken = searchParams.get("google_setup") || "";
  const googleEmail = searchParams.get("email") || "";
  const googleName = searchParams.get("name") || "";
  const googleError = searchParams.get("google_error") || "";
  const refCode = (searchParams.get("ref") || "").trim().slice(0, 200);
  const fromDemo = searchParams.get("from") === "demo";
  // Vertical toured in the demo — pre-selects the industry so onboarding
  // (FAQs, starters, widget defaults) matches what the visitor just saw.
  const demoVertical = (searchParams.get("vertical") || "").trim().slice(0, 50);
  const isGoogleSignup = Boolean(googleSetupToken);
  const [form, setForm] = useState(() => ({
    business_name: "",
    owner_name: googleName,
    email: googleEmail,
    password: "",
  }));
  const [showPassword, setShowPassword] = useState(false);
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

  function passwordProblem(pw) {
    if (pw.length < 10) return "Password needs at least 10 characters.";
    if (!/[A-Z]/.test(pw)) return "Password needs an uppercase letter.";
    if (!/[a-z]/.test(pw)) return "Password needs a lowercase letter.";
    if (!/[0-9]/.test(pw)) return "Password needs a number.";
    return "";
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!isGoogleSignup) {
      const problem = passwordProblem(form.password);
      if (problem) {
        setError(problem);
        return;
      }
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
          }
        : {
            business_name: form.business_name,
            owner_name: form.owner_name,
            email: form.email,
            password: form.password,
            ref_code: refCode || undefined,
            industry: demoVertical || undefined,
          };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = data.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : detail?.[0]?.msg || detail?.message || "Registration failed",
        );
      }

      const { token, tenant_id } = await res.json();
      localStorage.setItem("anx_token", token);
      localStorage.setItem("anx_tenant_id", tenant_id);
      trackEvent("sign_up", {
        method: isGoogleSignup ? "google" : "email",
        plan: checkoutPlan || "free",
        source: fromDemo ? "demo" : "direct",
      });

      if (fromDemo) {
        // Demo-to-signup attribution (fire-and-forget; readable via the
        // admin funnel readout). Never blocks the signup flow.
        fetch(`${API_BASE}/api/v1/wizard/${tenant_id}/event`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ step: 0, action: "demo_referral" }),
        }).catch(() => {});
      }

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

      window.location.href = "/setup";
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
      ? "Continue to checkout"
      : isGoogleSignup
        ? "Finish Google Signup"
        : "Meet your AI staff";

  return (
    <div className="login-page">
      <div className="login-card" style={{ width: 420 }}>
        <h1 className="login-title">AgentNexLiFy</h1>
        <p className="login-subtitle">
          {checkoutPlan
            ? "Create your account to continue to checkout"
            : "Hire your AI staff in under 2 minutes — free"}
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
            Using Google account <strong style={{ color: "var(--text-primary)" }}>{googleEmail}</strong>. One more field and you're in.
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
          {!isGoogleSignup && (
            <>
              <div className="login-field">
                <label>Your Name</label>
                <input
                  className="login-input"
                  value={form.owner_name}
                  onChange={update("owner_name")}
                  placeholder="Jane Smith"
                  required
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
                />
              </div>
              <div className="login-field">
                <label>Password</label>
                <div style={{ position: "relative" }}>
                  <input
                    type={showPassword ? "text" : "password"}
                    className="login-input"
                    value={form.password}
                    onChange={update("password")}
                    placeholder="10+ characters"
                    minLength={10}
                    required
                    style={{ paddingRight: "3.5rem", width: "100%", boxSizing: "border-box" }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    style={{
                      position: "absolute",
                      right: 10,
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "none",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                      padding: "4px",
                    }}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.35rem" }}>
                  At least 10 characters with an uppercase letter, a lowercase letter, and a number.
                </p>
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
