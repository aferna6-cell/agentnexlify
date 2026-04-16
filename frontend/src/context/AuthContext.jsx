import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";

const AuthContext = createContext(null);

const TOKEN_KEY = "anx_token";
const TENANT_KEY = "anx_tenant_id";

// Check token expiry every 60 seconds
const EXPIRY_CHECK_INTERVAL_MS = 60_000;

function parseJwt(token) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const logoutRef = useRef(null);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TENANT_KEY);
    setToken(null);
    setUser(null);
  }, []);

  // Keep ref in sync so interval callback always has latest logout
  logoutRef.current = logout;

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    const payload = parseJwt(token);
    if (!payload || (payload.exp && payload.exp * 1000 < Date.now())) {
      logout();
      return;
    }
    const tenantId = payload.tenant_id || payload.sub;
    localStorage.setItem(TENANT_KEY, tenantId);
    setUser({
      tenantId,
      email: payload.email,
      plan: payload.plan || "free",
      businessName: payload.business_name || "",
      businessType: payload.business_type || "",
      role: payload.role || "owner",
      isTeamMember: payload.is_team_member || false,
      name: payload.name || "",
      userId: payload.user_id || null,
      marketing_addon_active: false,
      marketing_addon_grandfathered: false,
    });

    // Fetch live add-on status from /me — JWT claims don't carry addon flags
    // and plan/addon data must come from live API (frontend-patterns.md).
    fetch(`${import.meta.env.VITE_API_URL || ""}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => {
        if (!me) return;
        setUser((prev) =>
          prev
            ? {
                ...prev,
                plan: me.plan || prev.plan,
                marketing_addon_active: Boolean(me.marketing_addon_active),
                marketing_addon_grandfathered: Boolean(
                  me.marketing_addon_grandfathered,
                ),
              }
            : prev,
        );
      })
      .catch((e) => {
        console.warn(
          "AuthContext: failed to fetch /me for addon flags",
          e?.message,
        );
      });

    // Proactive expiry check — logs out before next API call can 401
    const intervalId = setInterval(() => {
      const p = parseJwt(token);
      if (!p || (p.exp && p.exp * 1000 < Date.now())) {
        logoutRef.current();
        window.location.href = "/login?expired=1";
      }
    }, EXPIRY_CHECK_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [token, logout]);

  const login = useCallback((jwt) => {
    localStorage.setItem(TOKEN_KEY, jwt);
    setToken(jwt);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
