import { useState } from "react";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

const INDUSTRIES = [
  { value: "plumbing", label: "Plumbing" },
  { value: "dental", label: "Dental" },
  { value: "realestate", label: "Real Estate" },
  { value: "legal", label: "Legal" },
  { value: "fitness", label: "Fitness" },
  { value: "restaurant", label: "Restaurant" },
  { value: "salon", label: "Salon" },
  { value: "auto_shop", label: "Auto Shop" },
  { value: "medical", label: "Medical" },
  { value: "other", label: "Other" },
];

export default function SignupPage() {
  console.log('ENV:', import.meta.env.VITE_API_BASE_URL);
  const [form, setForm] = useState({
    business_name: "",
    owner_name: "",
    email: "",
    industry: "other",
    city: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      console.log('API URL:', `${API_BASE}/api/v1/auth/register`);
      const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: form.business_name,
          owner_name: form.owner_name,
          email: form.email,
          industry: form.industry,
          city: form.city,
          password: form.password,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Registration failed");
      }

      const { token, tenant_id } = await res.json();
      localStorage.setItem("anx_token", token);
      localStorage.setItem("anx_tenant_id", tenant_id);
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card" style={{ width: 420 }}>
        <h1 className="login-title">AgentNexLiFy</h1>
        <p className="login-subtitle">Create your free account</p>
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
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? "Creating account..." : "Get Started Free"}
          </button>
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
