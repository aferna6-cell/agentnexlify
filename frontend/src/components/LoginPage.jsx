import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://agentnexlify-production.up.railway.app";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    console.log('API URL:', import.meta.env.VITE_API_BASE_URL);
    console.log('Full login URL:', `${API_BASE}/api/v1/auth/login`);
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

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">AgentNexLiFy</h1>
        <p className="login-subtitle">Sign in to your dashboard</p>
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
          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
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
