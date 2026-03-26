import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

function getCallbackParams() {
  const searchParams = new URLSearchParams(window.location.search);
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const hashParams = new URLSearchParams(hash);

  return {
    token: hashParams.get("token") || searchParams.get("token") || "",
    tenantId: hashParams.get("tenant_id") || searchParams.get("tenant_id") || "",
  };
}

export default function AuthCallbackPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const { token, tenantId } = getCallbackParams();

    if (!token || !tenantId) {
      navigate("/login?google_error=missing_token", { replace: true });
      return;
    }

    localStorage.setItem("anx_token", token);
    localStorage.setItem("anx_tenant_id", tenantId);
    window.history.replaceState({}, document.title, "/dashboard");
    navigate("/dashboard", { replace: true });
  }, [navigate]);

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">Signing you in...</h1>
        <p className="login-subtitle">Completing Google authentication</p>
      </div>
    </div>
  );
}
