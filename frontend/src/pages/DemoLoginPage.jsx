import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { demoLogin } from "../utils/api/auth";

/**
 * /demo route - public, no auth guard.
 * On mount: calls demo-login endpoint, stores session via AuthContext.login()
 * (same path as a normal login), then redirects to /dashboard.
 *
 * The demo JWT carries role="demo". AuthContext parses it and surfaces
 * user.role, which DemoBanner reads to render the demo bar.
 */
export default function DemoLoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState(null);
  // /demo?vertical=salon picks the industry-matched demo tenant;
  // backend falls back to plumbing for absent/unknown values.
  const vertical = searchParams.get("vertical") || "";

  useEffect(() => {
    let cancelled = false;

    async function startDemo() {
      try {
        const data = await demoLogin(vertical);
        if (cancelled) return;
        // Store tenant_id first (mirrors LoginPage behaviour)
        localStorage.setItem("anx_tenant_id", data.tenant_id);
        // login() writes to localStorage and sets context token - same path
        // as the normal email/password login.
        login(data.token);
        navigate("/dashboard", { replace: true });
      } catch (err) {
        if (cancelled) return;
        setError(err.message || "Could not start demo. Please try again.");
      }
    }

    startDemo();
    return () => {
      cancelled = true;
    };
  }, [login, navigate, vertical]);

  if (error) {
    return (
      <div className="login-page">
        <div className="login-card">
          <h1 className="login-title">AgentNexLiFy</h1>
          <p className="login-subtitle">Live Demo</p>
          <div className="login-error" style={{ marginBottom: "1.25rem" }}>
            {error}
          </div>
          <a
            href="/"
            style={{
              display: "block",
              textAlign: "center",
              fontSize: "0.875rem",
              color: "var(--accent)",
              textDecoration: "none",
            }}
          >
            Back to homepage
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card" style={{ textAlign: "center" }}>
        <h1 className="login-title">AgentNexLiFy</h1>
        <p className="login-subtitle" style={{ marginBottom: "2rem" }}>
          Loading your demo environment&hellip;
        </p>
        <div
          style={{
            width: 36,
            height: 36,
            border: "3px solid rgba(255,255,255,0.1)",
            borderTopColor: "var(--accent)",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
            margin: "0 auto",
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  );
}
