import { useState, useEffect, useCallback } from "react";
import { BASE } from "../utils/api/_client";
import SkeletonLoader from "../components/SkeletonLoader";
import { notify } from "../utils/notify";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.9rem",
  boxSizing: "border-box",
};

const btnPrimary = {
  background: "var(--accent)",
  color: "#fff",
  border: "none",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 600,
  cursor: "pointer",
  fontSize: "0.9rem",
};

const btnSecondary = {
  background: "var(--bg-primary)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  padding: "8px 16px",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.85rem",
};

const btnDanger = {
  background: "rgba(248,113,113,0.15)",
  color: "#f87171",
  border: "1px solid rgba(248,113,113,0.3)",
  padding: "8px 16px",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.85rem",
};

const labelStyle = {
  display: "block",
  fontSize: "0.85rem",
  color: "var(--text-secondary)",
  marginBottom: 6,
};

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  borderRadius: 16,
  padding: "28px 32px",
  width: "90%",
  maxWidth: 600,
  maxHeight: "90vh",
  overflowY: "auto",
  border: "1px solid var(--border)",
};

const PROMOTION_TYPES = [
  {
    key: "free_tier",
    label: "Free Tier",
    desc: "Keep business on free plan indefinitely",
  },
  {
    key: "discount",
    label: "Discount",
    desc: "Percentage discount on any paid plan",
  },
  {
    key: "extended_trial",
    label: "Extended Trial",
    desc: "Longer than standard 7-day Growth trial",
  },
  {
    key: "partner_deal",
    label: "Partner Deal",
    desc: "Special arrangement with partner organization",
  },
  {
    key: "case_study",
    label: "Case Study",
    desc: "Free/discounted in exchange for case study",
  },
  { key: "referral", label: "Referral", desc: "Referred by another business" },
];

// Admin secret is entered at runtime via prompt - never baked into the JS bundle.
let _adminSecret = "";

function getAdminSecret() {
  if (!_adminSecret) {
    _adminSecret = window.prompt("Enter admin secret:") || "";
  }
  return _adminSecret;
}

function clearAdminSecret() {
  _adminSecret = "";
}

async function apiFetch(path, opts = {}) {
  const secret = getAdminSecret();
  if (!secret) throw new Error("No admin secret provided");
  const res = await fetch(`${BASE}/api/v1/admin${path}`, {
    headers: {
      "x-api-secret": secret,
      "Content-Type": "application/json",
      ...opts.headers,
    },
    ...opts,
  });
  if (res.status === 401) {
    clearAdminSecret();
    throw new Error("Invalid admin secret - cleared. Refresh to retry.");
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

function formatDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function TypeBadge({ type }) {
  const t = PROMOTION_TYPES.find((t) => t.key === type);
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: 12,
        fontSize: "0.75rem",
        fontWeight: 600,
        color: "var(--accent)",
        background: "var(--accent-dim)",
      }}
    >
      {t?.label || type}
    </span>
  );
}

function CreatePromotionModal({ onClose, onCreated }) {
  const [tenantId, setTenantId] = useState("");
  const [promotionType, setPromotionType] = useState("free_tier");
  const [discountPct, setDiscountPct] = useState(0);
  const [reason, setReason] = useState("");
  const [approvedBy, setApprovedBy] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [tenantSearch, setTenantSearch] = useState("");
  const [searchResults, setSearchResults] = useState([]);

  const searchTenants = async (query) => {
    if (!query.trim()) return;
    try {
      const res = await apiFetch(
        `/tenants?search=${encodeURIComponent(query)}&limit=10`,
      );
      setSearchResults(res.tenants || []);
    } catch {
      setSearchResults([]);
    }
  };

  const handleSubmit = async () => {
    if (!tenantId) {
      setError("Select a business first");
      return;
    }
    if (promotionType === "discount" && discountPct <= 0) {
      setError("Set a discount percentage");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch("/promotions", {
        method: "POST",
        body: JSON.stringify({
          tenant_id: tenantId,
          promotion_type: promotionType,
          discount_pct: discountPct,
          reason: reason.trim(),
          approved_by: approvedBy.trim(),
          expires_at: expiresAt || null,
          notes: notes.trim(),
        }),
      });
      onCreated();
    } catch (e) {
      setError(e.message || "Failed to create promotion");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <h2
          style={{
            margin: "0 0 20px",
            color: "var(--text-primary)",
            fontSize: "1.2rem",
          }}
        >
          Add Free / Discounted Business
        </h2>

        {/* Tenant Search */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Search Business</label>
          <input
            type="text"
            value={tenantSearch}
            onChange={(e) => {
              setTenantSearch(e.target.value);
              setTenantId("");
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                searchTenants(tenantSearch);
              }
            }}
            placeholder="Type business name or email and press Enter"
            style={inputStyle}
          />
          {searchResults.length > 0 && (
            <div
              style={{
                marginTop: 4,
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                maxHeight: 150,
                overflowY: "auto",
              }}
            >
              {searchResults.map((t) => (
                <div
                  key={t.id}
                  onClick={() => {
                    setTenantId(t.id);
                    setTenantSearch(t.business_name);
                    setSearchResults([]);
                  }}
                  style={{
                    padding: "8px 12px",
                    cursor: "pointer",
                    borderBottom: "1px solid var(--border)",
                    background:
                      tenantId === t.id ? "var(--accent-dim)" : "transparent",
                    color: "var(--text-primary)",
                    fontSize: "0.85rem",
                  }}
                >
                  <strong>{t.business_name}</strong> - {t.owner_email}
                  <span style={{ color: "var(--text-muted)", marginLeft: 8 }}>
                    ({t.plan})
                  </span>
                </div>
              ))}
            </div>
          )}
          {tenantId && (
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--green)",
                marginTop: 4,
              }}
            >
              \u2713 Selected
            </div>
          )}
        </div>

        {/* Promotion Type */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Arrangement Type</label>
          <select
            value={promotionType}
            onChange={(e) => setPromotionType(e.target.value)}
            style={inputStyle}
          >
            {PROMOTION_TYPES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label} - {t.desc}
              </option>
            ))}
          </select>
        </div>

        {/* Discount % (for discount type) */}
        {promotionType === "discount" && (
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Discount Percentage</label>
            <input
              type="number"
              min={1}
              max={100}
              value={discountPct}
              onChange={(e) => setDiscountPct(parseInt(e.target.value) || 0)}
              style={{ ...inputStyle, width: 120 }}
            />
            <span
              style={{
                fontSize: "0.85rem",
                color: "var(--text-muted)",
                marginLeft: 8,
              }}
            >
              %
            </span>
          </div>
        )}

        {/* Approved By */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Approved By</label>
          <input
            type="text"
            value={approvedBy}
            onChange={(e) => setApprovedBy(e.target.value)}
            placeholder="Who approved this arrangement?"
            style={inputStyle}
          />
        </div>

        {/* Reason */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Reason</label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why are we giving this arrangement?"
            style={inputStyle}
          />
        </div>

        {/* Expiry */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Expires At (optional)</label>
          <input
            type="date"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
            style={inputStyle}
          />
        </div>

        {/* Notes */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any additional context..."
            rows={3}
            style={{ ...inputStyle, resize: "vertical" }}
          />
        </div>

        {error && (
          <div
            style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{ ...btnPrimary, opacity: submitting ? 0.6 : 1 }}
          >
            {submitting ? "Creating..." : "Create Arrangement"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminPromotionsPage() {
  const [promotions, setPromotions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [filterType, setFilterType] = useState("");

  const loadPromotions = useCallback(async () => {
    if (!getAdminSecret()) return;
    setLoading(true);
    try {
      const params = filterType ? `?promotion_type=${filterType}` : "";
      const res = await apiFetch(`/promotions${params}`);
      setPromotions(res.promotions || []);
    } catch {
      setPromotions([]);
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  useEffect(() => {
    loadPromotions();
  }, [loadPromotions]);

  const handleExpire = async (id) => {
    try {
      await apiFetch(`/promotions/${id}/expire`, { method: "POST" });
      loadPromotions();
    } catch (e) {
      notify.error("Failed to expire: " + (e.message || "Unknown error"));
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this promotion arrangement?")) return;
    try {
      await apiFetch(`/promotions/${id}`, { method: "DELETE" });
      setPromotions((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      notify.error("Failed to delete: " + (e.message || "Unknown error"));
    }
  };

  if (!_adminSecret) {
    return (
      <div style={{ padding: "24px 32px", maxWidth: 1400 }}>
        <div
          style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}
        >
          <h2 style={{ color: "var(--text-primary)" }}>
            Admin Access Required
          </h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Refresh the page and enter the admin secret when prompted.
          </p>
        </div>
      </div>
    );
  }

  if (loading && promotions.length === 0) return <SkeletonLoader />;

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1200 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              margin: 0,
              color: "var(--text-primary)",
            }}
          >
            Free & Discounted Businesses
          </h1>
          <p
            style={{
              color: "var(--text-secondary)",
              margin: "4px 0 0",
              fontSize: "0.9rem",
            }}
          >
            Track businesses with special pricing arrangements
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} style={btnPrimary}>
          + Add Arrangement
        </button>
      </div>

      {/* Stats & Filters */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Total Arrangements", value: promotions.length },
          {
            label: "Active",
            value: promotions.filter(
              (p) => !p.expires_at || new Date(p.expires_at) > new Date(),
            ).length,
          },
          {
            label: "Expired",
            value: promotions.filter(
              (p) => p.expires_at && new Date(p.expires_at) <= new Date(),
            ).length,
          },
        ].map((s) => (
          <div key={s.label} style={cardStyle}>
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 4,
              }}
            >
              {s.label}
            </div>
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 240 }}
        >
          <option value="">All types</option>
          {PROMOTION_TYPES.map((t) => (
            <option key={t.key} value={t.key}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {/* Promotions List */}
      {promotions.length === 0 ? (
        <div
          style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}
        >
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>
            \ud83d\udcbc
          </div>
          <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>
            No arrangements yet
          </h3>
          <p style={{ color: "var(--text-secondary)", margin: "0 0 16px" }}>
            Track businesses you have given free access or discounts to
          </p>
          <button onClick={() => setShowCreate(true)} style={btnPrimary}>
            + Add First Arrangement
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {promotions.map((p) => {
            const tenant = Array.isArray(p.tenants)
              ? p.tenants[0] || {}
              : p.tenants || {};
            const isExpired =
              p.expires_at && new Date(p.expires_at) <= new Date();
            return (
              <div
                key={p.id}
                style={{
                  ...cardStyle,
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  opacity: isExpired ? 0.6 : 1,
                }}
              >
                <TypeBadge type={p.promotion_type} />
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontWeight: 600,
                      color: "var(--text-primary)",
                      marginBottom: 2,
                    }}
                  >
                    {tenant.business_name || "Unknown Business"}
                    {p.discount_pct > 0 && (
                      <span
                        style={{
                          marginLeft: 8,
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          color: "var(--green)",
                          background: "var(--green-dim)",
                          padding: "1px 8px",
                          borderRadius: 8,
                        }}
                      >
                        -{p.discount_pct}%
                      </span>
                    )}
                  </div>
                  <div
                    style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}
                  >
                    {tenant.owner_email} \u00b7{" "}
                    {tenant.business_type || "unknown"} \u00b7 Plan:{" "}
                    {tenant.plan || "free"}
                    {p.reason && <span> \u00b7 {p.reason}</span>}
                  </div>
                </div>
                <div
                  style={{
                    textAlign: "right",
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    flexShrink: 0,
                  }}
                >
                  <div>Started: {formatDate(p.starts_at || p.created_at)}</div>
                  {p.expires_at && (
                    <div
                      style={{
                        color: isExpired ? "#f87171" : "var(--text-secondary)",
                      }}
                    >
                      Expires: {formatDate(p.expires_at)}{" "}
                      {isExpired && "(expired)"}
                    </div>
                  )}
                  {p.approved_by && <div>By: {p.approved_by}</div>}
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  {!isExpired && p.expires_at && (
                    <button
                      onClick={() => handleExpire(p.id)}
                      style={{
                        ...btnSecondary,
                        padding: "4px 10px",
                        fontSize: "0.75rem",
                      }}
                    >
                      Expire
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(p.id)}
                    style={{
                      ...btnDanger,
                      padding: "4px 10px",
                      fontSize: "0.75rem",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <CreatePromotionModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            loadPromotions();
          }}
        />
      )}
    </div>
  );
}
