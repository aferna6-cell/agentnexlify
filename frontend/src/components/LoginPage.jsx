import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

export default function LoginPage() {
  const { login } = useAuth();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => {
    if (searchParams.get("expired")) {
      setError("Your session has expired. Please sign in again.");
    } else if (searchParams.get("google_error")) {
      setError("Google sign-in could not be completed. Please try again.");
    }
  }, [searchParams]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Invalid credentials");
      }
      const { token, tenant_id } = await res.json();
      localStorage.setItem("anx_tenant_id", tenant_id);
      login(token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleLogin() {
    setError("");
    setGoogleLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/google/url?mode=login`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.auth_url) {
        throw new Error(data.detail || "Google sign-in is not available yet");
      }
      window.location.href = data.auth_url;
    } catch (err) {
      setError(err.message);
      setGoogleLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">AgentNexLiFy</h1>
        <p className="login-subtitle">Sign in to your dashboard</p>
        <button
          type="button"
          className="login-btn"
          onClick={handleGoogleLogin}
          disabled={loading || googleLoading}
          style={{
            marginBottom: "1rem",
            background: "#fff",
            color: "#111827",
            border: "1px solid rgba(255,255,255,0.18)",
          }}
        >
          {googleLoading ? "Redirecting to Google..." : "Continue with Google"}
        </button>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            marginBottom: "1rem",
            color: "var(--text-muted)",
            fontSize: "0.85rem",
          }}
        >
          <span
            style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }}
          />
          <span>or sign in with email</span>
          <span
            style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }}
          />
        </div>
        <form onSubmit={handleSubmit}>
          <div className="login-field">
            <label>Email</label>
            <input
              type="email"
              className="login-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />
          </div>
          <div className="login-field">
            <label>Password</label>
            <input
              type="password"
              className="login-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button
            type="submit"
            className="login-btn"
            disabled={loading || googleLoading}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
          <div style={{ textAlign: "right", marginTop: "0.5rem" }}>
            <Link
              to="/forgot-password"
              style={{
                fontSize: "0.85rem",
                color: "var(--accent)",
                textDecoration: "none",
              }}
            >
              Forgot password?
            </Link>
          </div>
        </form>
        <p className="login-footer">
          Don't have an account?{" "}
          <Link to="/signup" className="login-link">
            Sign up free
          </Link>
        </p>
      </div>
    </div>
  );
}
