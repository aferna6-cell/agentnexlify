import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchProspectingStatus,
  searchProspects,
  fetchProspects,
  promoteProspect,
  rejectProspect,
} from "../utils/api/prospecting";
import { notify } from "../utils/notify";
import SkeletonLoader from "../components/SkeletonLoader";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const inputStyle = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.85rem",
  boxSizing: "border-box",
};

const btnPrimary = {
  background: "var(--accent)",
  color: "#fff",
  border: "none",
  padding: "9px 18px",
  borderRadius: 8,
  fontWeight: 600,
  cursor: "pointer",
  fontSize: "0.85rem",
};

function scoreBadgeStyle(score) {
  const n = Number(score) || 0;
  const cfg =
    n >= 80
      ? { color: "var(--green)", bg: "var(--green-dim)" }
      : n >= 50
        ? { color: "#f59e0b", bg: "rgba(245,158,11,0.14)" }
        : { color: "var(--text-muted)", bg: "var(--hover-overlay)" };
  return {
    display: "inline-block",
    padding: "2px 9px",
    borderRadius: 10,
    fontSize: "0.75rem",
    fontWeight: 700,
    color: cfg.color,
    background: cfg.bg,
  };
}

function statusPillColor(status) {
  if (status === "promoted") return { color: "var(--green)", bg: "var(--green-dim)" };
  if (status === "rejected")
    return { color: "#f87171", bg: "rgba(248,113,113,0.14)" };
  return { color: "var(--accent)", bg: "var(--accent-dim)" };
}

export default function ProspectingPage() {
  const { token } = useAuth();

  const [configured, setConfigured] = useState(null); // null = still checking
  const [prospects, setProspects] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");

  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [limit, setLimit] = useState(20);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [searchSummary, setSearchSummary] = useState(null);

  const [actioningId, setActioningId] = useState(null);

  const checkConfigured = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetchProspectingStatus(token);
      setConfigured(!!res?.configured);
    } catch (err) {
      console.error("Failed to load prospecting status", err);
      setConfigured(false);
    }
  }, [token]);

  const loadProspects = useCallback(async () => {
    if (!token) return;
    setLoadingList(true);
    try {
      const res = await fetchProspects(token, statusFilter || undefined);
      const list = Array.isArray(res) ? res : res?.prospects || [];
      setProspects(list);
      setListError(null);
    } catch (err) {
      console.error("Failed to load prospects", err);
      setListError(
        err?.message || "Couldn't load prospects. Please try again.",
      );
    } finally {
      setLoadingList(false);
    }
  }, [token, statusFilter]);

  useEffect(() => {
    checkConfigured();
  }, [checkConfigured]);

  useEffect(() => {
    loadProspects();
  }, [loadProspects]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim() || !location.trim()) {
      setSearchError("Enter what you're looking for and a location.");
      return;
    }
    setSearching(true);
    setSearchError(null);
    setSearchSummary(null);
    try {
      const res = await searchProspects(token, {
        query: query.trim(),
        location: location.trim(),
        limit,
      });
      setSearchSummary(res || {});
      await loadProspects();
      notify.success("Search complete.");
    } catch (err) {
      setSearchError(err?.message || "Search failed. Please try again.");
    } finally {
      setSearching(false);
    }
  };

  const handlePromote = async (id) => {
    setActioningId(id);
    try {
      await promoteProspect(token, id);
      setProspects((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: "promoted" } : p)),
      );
      notify.success("Prospect promoted to lead.");
    } catch (err) {
      notify.error(err?.message || "Failed to promote prospect.");
    } finally {
      setActioningId(null);
    }
  };

  const handleReject = async (id) => {
    setActioningId(id);
    try {
      await rejectProspect(token, id);
      setProspects((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: "rejected" } : p)),
      );
    } catch (err) {
      notify.error(err?.message || "Failed to reject prospect.");
    } finally {
      setActioningId(null);
    }
  };

  // Status tabs are built from what's actually in the data - the backend
  // owns the status enum, so the UI doesn't guess at values that don't exist.
  const statusCounts = {};
  prospects.forEach((p) => {
    const s = p.status || "new";
    statusCounts[s] = (statusCounts[s] || 0) + 1;
  });
  const statusKeys = Object.keys(statusCounts).sort();

  if (configured === null) return <SkeletonLoader />;
  if (loadingList && prospects.length === 0) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Prospecting</h1>
          <p>
            Find local businesses that match your ideal customer and promote
            the good ones straight to leads.
          </p>
        </div>
      </div>

      {!configured ? (
        <div className="empty-card">
          <p
            style={{
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: 8,
            }}
          >
            Prospecting isn't set up yet
          </p>
          <p>
            Business search needs a Google Places API key configured on the
            server (
            <code style={{ color: "var(--accent)" }}>
              GOOGLE_PLACES_API_KEY
            </code>
            ). Ask your admin to add it. Once it's set, come back here to
            search for local businesses by category and location, and promote
            the ones you like straight into your leads pipeline.
          </p>
        </div>
      ) : (
        <div style={{ ...cardStyle, marginBottom: 20 }}>
          <form
            onSubmit={handleSearch}
            style={{
              display: "flex",
              gap: 10,
              flexWrap: "wrap",
              alignItems: "flex-end",
            }}
          >
            <div style={{ flex: "2 1 220px" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                  marginBottom: 4,
                }}
              >
                What are you looking for
              </label>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g., roofing contractors"
                style={{ ...inputStyle, width: "100%" }}
              />
            </div>
            <div style={{ flex: "1 1 180px" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                  marginBottom: 4,
                }}
              >
                Location
              </label>
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g., Austin, TX"
                style={{ ...inputStyle, width: "100%" }}
              />
            </div>
            <div style={{ width: 90 }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                  marginBottom: 4,
                }}
              >
                Limit
              </label>
              <input
                type="number"
                min={1}
                max={100}
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value) || 20)}
                style={{ ...inputStyle, width: "100%" }}
              />
            </div>
            <button type="submit" style={btnPrimary} disabled={searching}>
              {searching ? "Searching..." : "Search"}
            </button>
          </form>
          {searchError && (
            <div
              style={{
                color: "#f87171",
                fontSize: "0.8rem",
                marginTop: 10,
              }}
            >
              {searchError}
            </div>
          )}
          {searchSummary && (
            <div
              style={{
                marginTop: 12,
                display: "flex",
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              {Object.entries(searchSummary)
                .filter(([, value]) => typeof value === "number")
                .map(([key, value]) => (
                  <div
                    key={key}
                    style={{
                      fontSize: "0.8rem",
                      color: "var(--text-secondary)",
                    }}
                  >
                    <strong style={{ color: "var(--text-primary)" }}>
                      {value}
                    </strong>{" "}
                    {key.replace(/_/g, " ")}
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {prospects.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: 6,
            marginBottom: 16,
            flexWrap: "wrap",
          }}
        >
          <button
            onClick={() => setStatusFilter("")}
            style={{
              padding: "6px 14px",
              borderRadius: 8,
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              border:
                statusFilter === ""
                  ? "2px solid var(--accent)"
                  : "1px solid var(--border)",
              background:
                statusFilter === ""
                  ? "var(--accent-dim)"
                  : "var(--bg-secondary)",
              color:
                statusFilter === "" ? "var(--accent)" : "var(--text-secondary)",
            }}
          >
            All ({prospects.length})
          </button>
          {statusKeys.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                fontSize: "0.8rem",
                fontWeight: 600,
                cursor: "pointer",
                textTransform: "capitalize",
                border:
                  statusFilter === s
                    ? "2px solid var(--accent)"
                    : "1px solid var(--border)",
                background:
                  statusFilter === s
                    ? "var(--accent-dim)"
                    : "var(--bg-secondary)",
                color:
                  statusFilter === s
                    ? "var(--accent)"
                    : "var(--text-secondary)",
              }}
            >
              {s} ({statusCounts[s]})
            </button>
          ))}
        </div>
      )}

      {listError ? (
        <div className="empty-card">
          <p
            style={{
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: 8,
            }}
          >
            Couldn't load prospects
          </p>
          <p>{listError}</p>
          <button
            className="btn-primary"
            onClick={loadProspects}
            style={{ marginTop: 12 }}
          >
            Retry
          </button>
        </div>
      ) : prospects.length === 0 ? (
        <div className="empty-card">
          <p
            style={{
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: 8,
            }}
          >
            No prospects yet
          </p>
          <p>
            {configured
              ? "Run a search above to find local businesses that match your ideal customer. Promote the good ones straight to leads, reject the rest."
              : "Once prospecting is configured, search results will show up here."}
          </p>
        </div>
      ) : (
        <div className="leads-table-wrapper">
          <table className="leads-table">
            <thead>
              <tr>
                <th>Business</th>
                <th>Category</th>
                <th>Address</th>
                <th>Phone</th>
                <th>Website</th>
                <th>Email</th>
                <th>Score</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {prospects.map((p) => {
                const status = (p.status || "new").toLowerCase();
                const isDecided = status === "promoted" || status === "rejected";
                const pill = statusPillColor(status);
                return (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 600 }}>
                      {p.business_name || "-"}
                    </td>
                    <td>{p.category || "-"}</td>
                    <td style={{ whiteSpace: "normal", maxWidth: 260 }}>
                      {p.address || "-"}
                    </td>
                    <td>{p.phone || "-"}</td>
                    <td>
                      {p.website ? (
                        <a
                          href={p.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: "var(--accent)" }}
                        >
                          Visit
                        </a>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td>
                      {p.email ? (
                        <span>
                          {p.email}{" "}
                          {p.email_verified && (
                            <span
                              title="Verified"
                              style={{
                                color: "var(--green)",
                                fontWeight: 700,
                              }}
                            >
                              &#10003;
                            </span>
                          )}
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td>
                      <span style={scoreBadgeStyle(p.score)}>
                        {p.score ?? "-"}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 9px",
                          borderRadius: 10,
                          fontSize: "0.72rem",
                          fontWeight: 600,
                          textTransform: "capitalize",
                          color: pill.color,
                          background: pill.bg,
                        }}
                      >
                        {status}
                      </span>
                    </td>
                    <td>
                      {isDecided ? (
                        <span
                          style={{
                            color: "var(--text-muted)",
                            fontSize: "0.75rem",
                            textTransform: "capitalize",
                          }}
                        >
                          {status}
                        </span>
                      ) : (
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            className="btn-sm"
                            onClick={() => handlePromote(p.id)}
                            disabled={actioningId === p.id}
                          >
                            {actioningId === p.id ? "..." : "Promote"}
                          </button>
                          <button
                            className="btn-sm"
                            onClick={() => handleReject(p.id)}
                            disabled={actioningId === p.id}
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
