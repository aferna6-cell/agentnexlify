import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchJobs,
  createJob,
  updateJob,
  deleteJob,
  fetchJobApplications,
  updateApplicationStatus,
} from "../utils/api";

const APP_STATUS_LABELS = {
  new: "New",
  contacted: "Contacted",
  interviewed: "Interviewed",
  hired: "Hired",
  rejected: "Rejected",
};

const APP_STATUS_COLORS = {
  new: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  contacted: { color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  interviewed: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  hired: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  rejected: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const emptyForm = {
  title: "",
  description: "",
  pay_range: "",
  schedule: "",
  location: "",
  skills: "",
};

export default function JobsPage() {
  const { user, token } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editJob, setEditJob] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });

  // Application state
  const [expandedJobId, setExpandedJobId] = useState(null);
  const [applications, setApplications] = useState([]);
  const [appsLoading, setAppsLoading] = useState(false);
  const [updatingAppId, setUpdatingAppId] = useState(null);

  // Toggling active/inactive
  const [togglingJobId, setTogglingJobId] = useState(null);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const data = await fetchJobs(user.tenantId, token);
      setJobs(data.jobs || data || []);
    } catch (err) {
      console.warn("Failed to load jobs:", err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const loadApplications = useCallback(
    async (jobId) => {
      if (!user?.tenantId) return;
      setAppsLoading(true);
      try {
        const data = await fetchJobApplications(user.tenantId, token, jobId);
        setApplications(data.applications || data || []);
      } catch (err) {
        console.warn("Failed to load applications:", err.message);
        setApplications([]);
      } finally {
        setAppsLoading(false);
      }
    },
    [user?.tenantId, token]
  );

  const handleExpandJob = (jobId) => {
    if (expandedJobId === jobId) {
      setExpandedJobId(null);
      setApplications([]);
      return;
    }
    setExpandedJobId(jobId);
    loadApplications(jobId);
  };

  const openCreate = () => {
    setEditJob(null);
    setForm({ ...emptyForm });
    setShowModal(true);
  };

  const openEdit = (job) => {
    setEditJob(job);
    setForm({
      title: job.title || "",
      description: job.description || "",
      pay_range: job.pay_range || "",
      schedule: job.schedule || "",
      location: job.location || "",
      skills: Array.isArray(job.skills) ? job.skills.join(", ") : job.skills || "",
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.title) return;
    setSaving(true);
    const body = {
      title: form.title,
      description: form.description || null,
      pay_range: form.pay_range || null,
      schedule: form.schedule || null,
      location: form.location || null,
      skills: form.skills
        ? form.skills
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        : [],
    };
    try {
      if (editJob) {
        await updateJob(user.tenantId, token, editJob.id, body);
      } else {
        await createJob(user.tenantId, token, body);
      }
      setShowModal(false);
      load();
    } catch (err) {
      console.warn("Save failed:", err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (jobId) => {
    if (!window.confirm("Delete this job posting? This cannot be undone.")) return;
    try {
      await deleteJob(user.tenantId, token, jobId);
      if (expandedJobId === jobId) {
        setExpandedJobId(null);
        setApplications([]);
      }
      load();
    } catch (err) {
      console.warn("Delete failed:", err.message);
    }
  };

  const handleToggleActive = async (job) => {
    setTogglingJobId(job.id);
    try {
      await updateJob(user.tenantId, token, job.id, {
        is_active: !job.is_active,
      });
      load();
    } catch (err) {
      console.warn("Toggle failed:", err.message);
    } finally {
      setTogglingJobId(null);
    }
  };

  const handleAppStatusChange = async (appId, newStatus) => {
    setUpdatingAppId(appId);
    try {
      await updateApplicationStatus(user.tenantId, token, appId, newStatus, null);
      setApplications((prev) =>
        prev.map((a) => (a.id === appId ? { ...a, status: newStatus } : a))
      );
    } catch (err) {
      console.warn("Application status update failed:", err.message);
    } finally {
      setUpdatingAppId(null);
    }
  };

  if (loading) return <SkeletonLoader />;

  const activeCount = jobs.filter((j) => j.is_active).length;
  const totalApps = jobs.reduce((sum, j) => sum + (j.application_count || 0), 0);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Job Board</h1>
          <p>Manage job postings and review applications</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              load();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={openCreate}>
            + Post a Job
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Total Postings", value: jobs.length, color: "var(--text-secondary)" },
          { label: "Active", value: activeCount, color: "#22c55e" },
          { label: "Inactive", value: jobs.length - activeCount, color: "var(--text-muted)" },
          { label: "Total Applications", value: totalApps, color: "#3b82f6" },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-color)",
              borderRadius: 12,
              padding: "16px 20px",
            }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>
              {card.label}
            </div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Job List */}
      {jobs.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>No job postings yet</div>
          <p style={{ maxWidth: 440, margin: "0 auto 20px" }}>
            Create your first job posting to start accepting applications. Job listings will appear
            on your public business page and can be shared with candidates.
          </p>
          <button className="btn-primary" onClick={openCreate}>
            Post Your First Job
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {jobs.map((job) => {
            const isExpanded = expandedJobId === job.id;
            return (
              <div key={job.id}>
                {/* Job Card */}
                <div
                  style={{
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: isExpanded ? "12px 12px 0 0" : 12,
                    padding: 16,
                    borderLeft: `4px solid ${job.is_active ? "#22c55e" : "var(--text-muted)"}`,
                    opacity: job.is_active ? 1 : 0.7,
                    cursor: "pointer",
                  }}
                  onClick={() => handleExpandJob(job.id)}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      flexWrap: "wrap",
                      gap: 8,
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 200 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          marginBottom: 6,
                        }}
                      >
                        <span style={{ fontWeight: 600, fontSize: "1rem" }}>{job.title}</span>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "2px 8px",
                            borderRadius: 4,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            color: job.is_active ? "#22c55e" : "var(--text-muted)",
                            background: job.is_active
                              ? "rgba(34,197,94,0.1)"
                              : "var(--hover-overlay)",
                          }}
                        >
                          {job.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: 12,
                          fontSize: "0.8rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        {job.pay_range && <span>Pay: {job.pay_range}</span>}
                        {job.schedule && <span>Schedule: {job.schedule}</span>}
                        {job.location && <span>Location: {job.location}</span>}
                      </div>
                      {job.skills && (Array.isArray(job.skills) ? job.skills : []).length > 0 && (
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 4,
                            marginTop: 8,
                          }}
                        >
                          {(Array.isArray(job.skills) ? job.skills : []).map((skill, idx) => (
                            <span
                              key={idx}
                              style={{
                                display: "inline-block",
                                padding: "2px 8px",
                                borderRadius: 4,
                                fontSize: "0.7rem",
                                fontWeight: 500,
                                color: "var(--text-secondary)",
                                background: "var(--hover-overlay)",
                              }}
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#3b82f6" }}>
                          {job.application_count || 0} application
                          {(job.application_count || 0) !== 1 ? "s" : ""}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          {formatDate(job.created_at)}
                        </div>
                      </div>
                      <div
                        style={{ display: "flex", gap: 6 }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => handleToggleActive(job)}
                          disabled={togglingJobId === job.id}
                          style={{
                            background: "none",
                            border: "1px solid var(--border-color)",
                            borderRadius: 6,
                            padding: "6px 10px",
                            color: job.is_active ? "var(--text-muted)" : "#22c55e",
                            cursor: "pointer",
                            fontSize: "0.8rem",
                          }}
                        >
                          {togglingJobId === job.id
                            ? "..."
                            : job.is_active
                            ? "Deactivate"
                            : "Activate"}
                        </button>
                        <button
                          onClick={() => openEdit(job)}
                          style={{
                            background: "none",
                            border: "1px solid var(--border-color)",
                            borderRadius: 6,
                            padding: "6px 10px",
                            color: "var(--text-secondary)",
                            cursor: "pointer",
                            fontSize: "0.8rem",
                          }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(job.id)}
                          style={{
                            background: "none",
                            border: "1px solid var(--border-color)",
                            borderRadius: 6,
                            padding: "6px 10px",
                            color: "var(--red, #ef4444)",
                            cursor: "pointer",
                            fontSize: "0.8rem",
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Expanded Applications Section */}
                {isExpanded && (
                  <div
                    style={{
                      background: "var(--bg-primary)",
                      border: "1px solid var(--border-color)",
                      borderTop: "none",
                      borderRadius: "0 0 12px 12px",
                      padding: 16,
                    }}
                  >
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        marginBottom: 12,
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      Applications
                    </div>

                    {appsLoading ? (
                      <div
                        style={{
                          padding: "20px 0",
                          textAlign: "center",
                          color: "var(--text-muted)",
                          fontSize: "0.85rem",
                        }}
                      >
                        Loading applications...
                      </div>
                    ) : applications.length === 0 ? (
                      <div
                        style={{
                          padding: "24px 0",
                          textAlign: "center",
                          color: "var(--text-muted)",
                        }}
                      >
                        <div style={{ fontSize: "1rem", marginBottom: 4 }}>
                          No applications yet
                        </div>
                        <p style={{ fontSize: "0.8rem", maxWidth: 360, margin: "0 auto" }}>
                          Share this job posting to start receiving applications. Applicants will
                          appear here as they apply.
                        </p>
                      </div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {applications.map((app) => {
                          const statusInfo =
                            APP_STATUS_COLORS[app.status] || APP_STATUS_COLORS.new;
                          return (
                            <div
                              key={app.id}
                              style={{
                                background: "var(--bg-secondary)",
                                border: "1px solid var(--border-color)",
                                borderRadius: 8,
                                padding: 12,
                              }}
                            >
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "flex-start",
                                  flexWrap: "wrap",
                                  gap: 8,
                                }}
                              >
                                <div style={{ flex: 1, minWidth: 180 }}>
                                  <div
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: 8,
                                      marginBottom: 4,
                                    }}
                                  >
                                    <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                                      {app.applicant_name || "Unknown Applicant"}
                                    </span>
                                    <span
                                      style={{
                                        display: "inline-block",
                                        padding: "2px 8px",
                                        borderRadius: 4,
                                        fontSize: "0.7rem",
                                        fontWeight: 600,
                                        color: statusInfo.color,
                                        background: statusInfo.bg,
                                      }}
                                    >
                                      {APP_STATUS_LABELS[app.status] || app.status}
                                    </span>
                                  </div>
                                  {app.phone && (
                                    <div
                                      style={{
                                        fontSize: "0.8rem",
                                        color: "var(--text-secondary)",
                                        marginBottom: 2,
                                      }}
                                    >
                                      Phone: {app.phone}
                                    </div>
                                  )}
                                  {app.email && (
                                    <div
                                      style={{
                                        fontSize: "0.8rem",
                                        color: "var(--text-secondary)",
                                        marginBottom: 2,
                                      }}
                                    >
                                      Email: {app.email}
                                    </div>
                                  )}
                                  {app.message && (
                                    <div
                                      style={{
                                        fontSize: "0.8rem",
                                        color: "var(--text-muted)",
                                        marginTop: 6,
                                        lineHeight: 1.4,
                                        fontStyle: "italic",
                                      }}
                                    >
                                      "{app.message}"
                                    </div>
                                  )}
                                </div>
                                <div
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 8,
                                  }}
                                >
                                  <div
                                    style={{
                                      fontSize: "0.75rem",
                                      color: "var(--text-muted)",
                                      textAlign: "right",
                                      whiteSpace: "nowrap",
                                    }}
                                  >
                                    {timeAgo(app.created_at)}
                                  </div>
                                  <select
                                    value={app.status || "new"}
                                    onChange={(e) =>
                                      handleAppStatusChange(app.id, e.target.value)
                                    }
                                    disabled={updatingAppId === app.id}
                                    style={{
                                      padding: "4px 8px",
                                      borderRadius: 6,
                                      border: "1px solid var(--border-color)",
                                      background: "var(--bg-primary)",
                                      color: "var(--text-primary)",
                                      fontSize: "0.8rem",
                                      cursor: "pointer",
                                    }}
                                  >
                                    {Object.entries(APP_STATUS_LABELS).map(([k, v]) => (
                                      <option key={k} value={k}>
                                        {v}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{
              background: "var(--bg-primary)",
              borderRadius: 12,
              padding: 24,
              width: "90%",
              maxWidth: 520,
              maxHeight: "80vh",
              overflowY: "auto",
              border: "1px solid var(--border-color)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>
              {editJob ? "Edit Job Posting" : "Post a New Job"}
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.8rem",
                    marginBottom: 4,
                    color: "var(--text-secondary)",
                  }}
                >
                  Job Title *
                </label>
                <input
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="e.g. Line Cook, Front Desk Receptionist"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.8rem",
                    marginBottom: 4,
                    color: "var(--text-secondary)",
                  }}
                >
                  Description
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Describe the role, responsibilities, and what you're looking for..."
                  rows={4}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>
              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.8rem",
                      marginBottom: 4,
                      color: "var(--text-secondary)",
                    }}
                  >
                    Pay Range
                  </label>
                  <input
                    value={form.pay_range}
                    onChange={(e) => setForm((f) => ({ ...f, pay_range: e.target.value }))}
                    placeholder="e.g. $15-20/hr, $50k-60k/yr"
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.8rem",
                      marginBottom: 4,
                      color: "var(--text-secondary)",
                    }}
                  >
                    Schedule
                  </label>
                  <input
                    value={form.schedule}
                    onChange={(e) => setForm((f) => ({ ...f, schedule: e.target.value }))}
                    placeholder="e.g. Full-time, Part-time, Weekends"
                  />
                </div>
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.8rem",
                    marginBottom: 4,
                    color: "var(--text-secondary)",
                  }}
                >
                  Location
                </label>
                <input
                  value={form.location}
                  onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                  placeholder="e.g. 123 Main St, Remote, On-site"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.8rem",
                    marginBottom: 4,
                    color: "var(--text-secondary)",
                  }}
                >
                  Required Skills (comma-separated)
                </label>
                <input
                  value={form.skills}
                  onChange={(e) => setForm((f) => ({ ...f, skills: e.target.value }))}
                  placeholder="e.g. Customer service, Food handling, Spanish"
                  style={{ width: "100%" }}
                />
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowModal(false)}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border-color)",
                  borderRadius: 8,
                  padding: "8px 16px",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={!form.title || saving}
              >
                {saving ? "Saving..." : editJob ? "Save Changes" : "Post Job"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
