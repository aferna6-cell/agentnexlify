import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

export default function ClientLoginPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [businessName, setBusinessName] = useState("");

  // Try to get business name from the slug
  useEffect(() => {
    if (!slug) return;
    fetch(`${API_BASE}/api/v1/business/${slug}`)
      .then((res) => res.ok ? res.json() : null)
      .then((data) => {
        if (data?.business_name) setBusinessName(data.business_name);
      })
      .catch((e) => { console.warn('Business name fetch failed:', e?.message); });
  }, [slug]);

  // Check if already logged in
  useEffect(() => {
    const token = sessionStorage.getItem(`client_token_${slug}`);
    if (token) navigate(`/client/dashboard/${slug}`);
  }, [slug, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/portal/client/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, business_slug: slug }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Login failed");
      sessionStorage.setItem(`client_token_${slug}`, data.token);
      navigate(`/client/dashboard/${slug}`);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const styles = {
    wrapper: {
      minHeight: "100vh",
      background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "'Inter', -apple-system, sans-serif",
      padding: "20px",
    },
    card: {
      background: "rgba(30, 27, 75, 0.6)",
      border: "1px solid rgba(99, 102, 241, 0.2)",
      borderRadius: "16px",
      padding: "40px",
      width: "100%",
      maxWidth: "400px",
      backdropFilter: "blur(20px)",
    },
    title: {
      color: "#fff",
      fontSize: "24px",
      fontWeight: 700,
      textAlign: "center",
      margin: "0 0 8px 0",
    },
    subtitle: {
      color: "rgba(255,255,255,0.5)",
      fontSize: "14px",
      textAlign: "center",
      margin: "0 0 32px 0",
    },
    label: {
      color: "rgba(255,255,255,0.7)",
      fontSize: "13px",
      fontWeight: 500,
      display: "block",
      marginBottom: "6px",
    },
    input: {
      width: "100%",
      padding: "12px 14px",
      background: "rgba(15, 23, 42, 0.8)",
      border: "1px solid rgba(99, 102, 241, 0.2)",
      borderRadius: "8px",
      color: "#fff",
      fontSize: "14px",
      outline: "none",
      marginBottom: "20px",
      boxSizing: "border-box",
    },
    button: {
      width: "100%",
      padding: "12px",
      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
      border: "none",
      borderRadius: "8px",
      color: "#fff",
      fontSize: "15px",
      fontWeight: 600,
      cursor: "pointer",
      opacity: loading ? 0.6 : 1,
    },
    error: {
      background: "rgba(239, 68, 68, 0.1)",
      border: "1px solid rgba(239, 68, 68, 0.3)",
      borderRadius: "8px",
      padding: "10px 14px",
      color: "#fca5a5",
      fontSize: "13px",
      marginBottom: "20px",
      textAlign: "center",
    },
    businessBadge: {
      display: "inline-block",
      background: "rgba(99, 102, 241, 0.15)",
      color: "#a5b4fc",
      fontSize: "12px",
      fontWeight: 500,
      padding: "4px 10px",
      borderRadius: "12px",
      marginBottom: "24px",
      textAlign: "center",
      width: "fit-content",
      margin: "0 auto 24px",
    },
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h1 style={styles.title}>Client Portal</h1>
        <p style={styles.subtitle}>Sign in to view your account</p>
        {businessName && (
          <div style={{ textAlign: "center" }}>
            <div style={styles.businessBadge}>{businessName}</div>
          </div>
        )}
        {error && <div style={styles.error}>{error}</div>}
        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Email</label>
          <input
            style={styles.input}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            required
          />
          <label style={styles.label}>Password</label>
          <input
            style={styles.input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            required
          />
          <button style={styles.button} type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
