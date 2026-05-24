import { trackEvent } from "../../utils/analytics";

export default function StripeCta({ plan, children }) {
  const handleClick = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("anx_token");
    if (!token) {
      window.location.href = `/signup?plan=${encodeURIComponent(plan)}`;
      return;
    }
    trackEvent("begin_checkout", { event_label: "home_pricing", plan });
    try {
      const API =
        import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";
      const resp = await fetch(`${API}/api/v1/auth/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plan }),
      });
      const data = await resp.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        window.location.href = "/signup";
      }
    } catch {
      window.location.href = "/signup";
    }
  };
  return (
    <a href="/signup" onClick={handleClick} className="pricing-cta">
      {children}
    </a>
  );
}
