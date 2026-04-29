import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { notify } from "../utils/notify";
import {
  fetchMarketingCampaigns,
  createMarketingCampaign,
  sendMarketingCampaign,
  fetchCampaignDetail,
  fetchCampaignAnalytics,
  generateCampaignContent,
  estimateCampaignRecipients,
} from "../utils/api/campaigns";
import { fetchTagDefinitions } from "../utils/api/tags";
import { fetchDashboard } from "../utils/api/dashboard";
import SkeletonLoader from "../components/SkeletonLoader";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import UpgradePrompt, { planBelowRequired } from "../components/UpgradePrompt";

/* ---- Constants ---- */

const CAMPAIGN_TYPES = [
  { key: "email", label: "Email", color: "var(--accent)", icon: "\u2709" },
  { key: "sms", label: "SMS", color: "var(--green)", icon: "\u2709" },
];

const STATUS_STYLES = {
  draft: { label: "Draft", color: "var(--text-secondary)", bg: "var(--hover-overlay)" },
  scheduled: { label: "Scheduled", color: "var(--purple, #8b5cf6)", bg: "rgba(139, 92, 246, 0.15)" },
  sending: { label: "Sending", color: "var(--yellow, #f59e0b)", bg: "rgba(245, 158, 11, 0.15)" },
  sent: { label: "Sent", color: "var(--green)", bg: "var(--green-dim)" },
  failed: { label: "Failed", color: "#f87171", bg: "rgba(248, 113, 113, 0.15)" },
};

const LEAD_STATUSES = ["new", "contacted", "booked", "completed", "lost"];
const LEAD_TEMPS = ["hot", "warm", "cold"];
const CAMPAIGN_PURPOSES = ["promotional", "newsletter", "announcement", "follow_up", "seasonal"];
const TONES = ["professional", "casual", "friendly", "urgent"];

const SMS_CHAR_LIMIT = 160;

/* ---- Helpers ---- */

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.draft;
  return (
    <span style={{
      padding: "2px 10px", borderRadius: 12, fontSize: "0.75rem", fontWeight: 600,
      color: s.color, background: s.bg,
    }}>
      {s.label}
    </span>
  );
}

function TypeBadge({ type }) {
  const t = CAMPAIGN_TYPES.find((c) => c.key === type) || CAMPAIGN_TYPES[0];
  return (
    <span style={{
      padding: "2px 10px", borderRadius: 12, fontSize: "0.75rem", fontWeight: 600,
      color: t.color, background: `${t.color}15`,
    }}>
      {t.icon} {t.label}
    </span>
  );
}

function formatDate(dateStr) {
  if (!dateStr) return "\u2014";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function formatPercent(num) {
  if (num === undefined || num === null) return "\u2014";
  return `${Math.round(num * 100) / 100}%`;
}

/* ---- Shared styles ---- */

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const inputStyle = {
  width: "100%", padding: "10px 14px", borderRadius: 8,
  border: "1px solid var(--border)", background: "var(--bg-primary)",
  color: "var(--text-primary)", fontSize: "0.9rem", boxSizing: "border-box",
};

const btnPrimary = {
  background: "var(--accent)", color: "#fff", border: "none",
  padding: "10px 20px", borderRadius: 8, fontWeight: 600, cursor: "pointer", fontSize: "0.9rem",
};

const btnSecondary = {
  background: "var(--bg-primary)", color: "var(--text-secondary)",
  border: "1px solid var(--border)", padding: "8px 16px",
  borderRadius: 8, cursor: "pointer", fontSize: "0.85rem",
};

const labelStyle = {
  display: "block", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 6,
};

const overlayStyle = {
  position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
  display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
};

const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))", borderRadius: 16,
  padding: "28px 32px", width: "90%", maxWidth: 750, maxHeight: "90vh",
  overflowY: "auto", border: "1px solid var(--border)",
};

/* ==== Main Component ==== */

export default function MarketingCampaignsPage({ onNavigate }) {
  const { user, token } = useAuth();

  // Plan gating - use live plan from API, fall back to JWT only as initial value
  const [livePlan, setLivePlan] = useState(user?.plan || "free");
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);

  // Data state
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [campaignDetail, setCampaignDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  /* ---- Load data ---- */

  const loadCampaigns = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const res = await fetchMarketingCampaigns(user.tenantId, token, {
        type: typeFilter || undefined,
        status: statusFilter || undefined,
      });
      setCampaigns(res.campaigns || res || []);
    } catch {
      setCampaigns([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, typeFilter, statusFilter]);

  useEffect(() => {
    loadCampaigns();
    if (user?.tenantId) {
      fetchDashboard(user.tenantId, token)
        .then((res) => { if (res?.plan) setLivePlan(res.plan); })
        .catch((e) => { console.warn('Dashboard fetch failed, using JWT plan fallback:', e?.message); }); // non-critical - JWT plan is the fallback
    }
  }, [loadCampaigns, user?.tenantId, token]);

  /* ---- Open campaign detail ---- */

  const openDetail = async (campaign) => {
    setSelectedCampaign(campaign);
    setDetailLoading(true);
    setCampaignDetail(null);
    try {
      const [detail, analytics] = await Promise.all([
        fetchCampaignDetail(user.tenantId, token, campaign.id).catch((e) => { console.warn('Failed to load campaign detail:', e?.message); return null; }),
        fetchCampaignAnalytics(user.tenantId, token, campaign.id).catch((e) => { console.warn('Failed to load campaign analytics:', e?.message); return null; }),
      ]);
      setCampaignDetail({ ...(detail || campaign), analytics: analytics || null });
    } catch {
      setCampaignDetail(campaign);
    } finally {
      setDetailLoading(false);
    }
  };

  /* ---- Send campaign ---- */

  const handleSendCampaign = async (campaignId) => {
    if (!confirm("Send this campaign now? This will deliver it to all matching recipients.")) return;
    try {
      await sendMarketingCampaign(user.tenantId, token, campaignId);
      loadCampaigns();
      if (selectedCampaign?.id === campaignId) {
        openDetail({ ...selectedCampaign, status: "sending" });
      }
    } catch (e) {
      notify.error("Failed to send: " + (e.message || "Unknown error"));
    }
  };

  /* ---- Computed ---- */

  const campaignsArray = Array.isArray(campaigns) ? campaigns : [];
  const totalCampaigns = campaignsArray.length;
  const sentCount = campaignsArray.filter((c) => c.status === "sent").length;
  const draftCount = campaignsArray.filter((c) => c.status === "draft").length;
  const avgOpenRate = (() => {
    const sent = campaignsArray.filter((c) => c.open_rate != null);
    if (sent.length === 0) return null;
    return Math.round((sent.reduce((sum, c) => sum + c.open_rate, 0) / sent.length) * 100) / 100;
  })();

  /* ---- Render ---- */

  if (loading && campaignsArray.length === 0) return <SkeletonLoader />;

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1200 }}>
      {/* Upgrade prompt modal */}
      {showUpgradePrompt && (
        <UpgradePrompt
          feature="Marketing Campaigns"
          requiredPlan="growth"
          onClose={() => setShowUpgradePrompt(false)}
          onNavigate={onNavigate}
        />
      )}

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
            Marketing Campaigns
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: "4px 0 0", fontSize: "0.9rem" }}>
            Create and send targeted email and SMS campaigns to your leads
          </p>
        </div>
        <button
          onClick={() => {
            if (planBelowRequired(livePlan, "growth")) {
              setShowUpgradePrompt(true);
            } else {
              setShowCreate(true);
            }
          }}
          style={btnPrimary}
        >
          + Create Campaign
        </button>
      </div>

      {/* Plan gate banner for free users */}
      {planBelowRequired(livePlan, "growth") && (
        <UpgradePrompt
          feature="Marketing Campaigns"
          requiredPlan="growth"
          onClose={() => {}}
          onNavigate={onNavigate}
          variant="banner"
        />
      )}

      {/* Stat Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Total Campaigns", value: totalCampaigns, color: "var(--accent)" },
          { label: "Sent", value: sentCount, color: "var(--green)" },
          { label: "Drafts", value: draftCount, color: "var(--text-secondary)" },
          { label: "Avg Open Rate", value: avgOpenRate !== null ? `${avgOpenRate}%` : "--", color: "var(--purple, #8b5cf6)" },
        ].map((s) => (
          <div key={s.label} style={cardStyle}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center" }}>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 160 }}>
          <option value="">All types</option>
          <option value="email">Email</option>
          <option value="sms">SMS</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 160 }}>
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="scheduled">Scheduled</option>
          <option value="sent">Sent</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Campaign List */}
      {campaignsArray.length === 0 ? (
        <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>&#128232;</div>
          <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>No campaigns yet</h3>
          <p style={{ color: "var(--text-secondary)", margin: "0 0 16px", maxWidth: 440, marginInline: "auto" }}>
            Create your first marketing campaign to reach your leads via email or SMS.
            Target specific segments based on lead status, temperature, or tags.
            Use AI to generate compelling content automatically.
          </p>
          <button onClick={() => setShowCreate(true)} style={btnPrimary}>
            + Create Campaign
          </button>
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{
            width: "100%", borderCollapse: "separate", borderSpacing: 0,
            background: "var(--bg-secondary, var(--card-bg))", border: "1px solid var(--border)",
            borderRadius: 12, overflow: "hidden",
          }}>
            <thead>
              <tr>
                {["Name", "Type", "Status", "Recipients", "Open Rate", "Sent Date", "Actions"].map((h) => (
                  <th key={h} style={{
                    textAlign: "left", padding: "12px 16px", fontSize: "0.8rem",
                    color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border)",
                    textTransform: "uppercase", letterSpacing: "0.05em",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {campaignsArray.map((c) => (
                <tr key={c.id} onClick={() => openDetail(c)} style={{ cursor: "pointer", transition: "background 0.15s" }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "var(--hover-overlay)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
                  <td style={{ padding: "12px 16px", color: "var(--text-primary)", fontWeight: 600 }}>
                    {c.name || "Untitled Campaign"}
                  </td>
                  <td style={{ padding: "12px 16px" }}><TypeBadge type={c.type} /></td>
                  <td style={{ padding: "12px 16px" }}><StatusBadge status={c.status} /></td>
                  <td style={{ padding: "12px 16px", color: "var(--text-secondary)" }}>
                    {c.recipient_count ?? "\u2014"}
                  </td>
                  <td style={{ padding: "12px 16px", color: "var(--text-secondary)" }}>
                    {formatPercent(c.open_rate)}
                  </td>
                  <td style={{ padding: "12px 16px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {formatDate(c.sent_at)}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    {c.status === "draft" && (
                      <button onClick={(e) => { e.stopPropagation(); handleSendCampaign(c.id); }}
                        style={{ ...btnPrimary, padding: "5px 12px", fontSize: "0.8rem" }}>
                        Send
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ============ CAMPAIGN DETAIL PANEL ============ */}
      {selectedCampaign && (
        <CampaignDetailPanel
          campaign={campaignDetail || selectedCampaign}
          loading={detailLoading}
          onClose={() => { setSelectedCampaign(null); setCampaignDetail(null); }}
          onSend={() => handleSendCampaign(selectedCampaign.id)}
        />
      )}

      {/* ============ CREATE CAMPAIGN MODAL ============ */}
      {showCreate && (
        <CreateCampaignModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); loadCampaigns(); }}
        />
      )}
    </div>
  );
}

/* ==== Campaign Detail Panel ==== */

function CampaignDetailPanel({ campaign, loading, onClose, onSend }) {
  const analytics = campaign?.analytics;

  const statsData = analytics ? [
    { label: "Sent", value: analytics.sent || 0, color: "var(--accent)" },
    { label: "Delivered", value: analytics.delivered || 0, color: "var(--green)" },
    { label: "Opened", value: analytics.opened || 0, color: "var(--purple, #8b5cf6)" },
    { label: "Clicked", value: analytics.clicked || 0, color: "var(--yellow, #f59e0b)" },
    { label: "Bounced", value: analytics.bounced || 0, color: "#f87171" },
  ] : [];

  const chartData = statsData.length > 0 ? statsData.map((s) => ({ name: s.label, value: s.value })) : [];

  return (
    <div style={{ ...cardStyle, marginTop: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--text-primary)" }}>
            {campaign.name || "Campaign Details"}
          </h2>
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 10, alignItems: "center" }}>
            <TypeBadge type={campaign.type} />
            <StatusBadge status={campaign.status} />
            {campaign.sent_at && <span>Sent {formatDate(campaign.sent_at)}</span>}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {campaign.status === "draft" && (
            <button onClick={onSend} style={{ ...btnPrimary, padding: "8px 16px", fontSize: "0.85rem" }}>
              Send Now
            </button>
          )}
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}>
            &#x2715;
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>Loading details...</div>
      ) : (
        <>
          {/* Stats Cards */}
          {analytics && statsData.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 24 }}>
              {statsData.map((s) => (
                <div key={s.label} style={{
                  background: "var(--bg-primary)", border: "1px solid var(--border)",
                  borderRadius: 8, padding: "12px 16px", textAlign: "center",
                }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>{s.label}</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: s.color }}>{s.value}</div>
                </div>
              ))}
            </div>
          )}

          {/* Open / Click Rates */}
          {analytics && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
              <RateIndicator label="Open Rate" rate={analytics.open_rate} color="var(--accent)" />
              <RateIndicator label="Click Rate" rate={analytics.click_rate} color="var(--green)" />
            </div>
          )}

          {/* Funnel Chart */}
          {analytics && chartData.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h3 style={{ fontSize: "0.95rem", color: "var(--text-primary)", margin: "0 0 12px" }}>Delivery Funnel</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-primary)" }} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="var(--accent)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Campaign Content Preview */}
          {(campaign.subject || campaign.body || campaign.body_html) && (
            <div style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 8, padding: 16 }}>
              <h3 style={{ fontSize: "0.95rem", color: "var(--text-primary)", margin: "0 0 8px" }}>Content Preview</h3>
              {campaign.subject && (
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Subject: </span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{campaign.subject}</span>
                </div>
              )}
              <div style={{ fontSize: "0.9rem", color: "var(--text-primary)", whiteSpace: "pre-wrap", lineHeight: 1.6, maxHeight: 300, overflowY: "auto" }}>
                {campaign.body || campaign.body_html || "No content"}
              </div>
            </div>
          )}

          {/* Recipients */}
          {campaign.recipients && Array.isArray(campaign.recipients) && campaign.recipients.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h3 style={{ fontSize: "0.95rem", color: "var(--text-primary)", margin: "0 0 12px" }}>
                Recipients ({campaign.recipients.length})
              </h3>
              <div style={{ maxHeight: 200, overflowY: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {["Name", "Email", "Status"].map((h) => (
                        <th key={h} style={{
                          textAlign: "left", padding: "8px 12px", fontSize: "0.75rem",
                          color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border)",
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {campaign.recipients.map((r, i) => (
                      <tr key={i}>
                        <td style={{ padding: "8px 12px", color: "var(--text-primary)", fontSize: "0.85rem" }}>{r.name || "\u2014"}</td>
                        <td style={{ padding: "8px 12px", color: "var(--text-secondary)", fontSize: "0.85rem" }}>{r.email || r.phone || "\u2014"}</td>
                        <td style={{ padding: "8px 12px" }}>
                          <StatusBadge status={r.status || "sent"} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Empty analytics state */}
          {!analytics && campaign.status === "draft" && (
            <div style={{ textAlign: "center", padding: "24px 16px", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
              Analytics will appear after this campaign is sent. Click "Send Now" to deliver it to your audience.
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ==== Rate Indicator ==== */

function RateIndicator({ label, rate, color }) {
  const pct = rate != null ? Math.round(rate * 100) / 100 : 0;
  return (
    <div style={{
      background: "var(--bg-primary)", border: "1px solid var(--border)",
      borderRadius: 8, padding: "16px 20px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{label}</span>
        <span style={{ fontSize: "1.1rem", fontWeight: 700, color }}>{pct}%</span>
      </div>
      <div style={{ height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${Math.min(pct, 100)}%`, background: color, borderRadius: 3, transition: "width 0.3s" }} />
      </div>
    </div>
  );
}

/* ==== Create Campaign Modal ==== */

function CreateCampaignModal({ tenantId, token, onClose, onCreated }) {
  // Form state
  const [name, setName] = useState("");
  const [type, setType] = useState("email");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("");
  const [sendNow, setSendNow] = useState(false);

  // Target audience
  const [statusFilter, setStatusFilter] = useState("");
  const [tempFilter, setTempFilter] = useState("");
  const [selectedTags, setSelectedTags] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);
  const [estimatedRecipients, setEstimatedRecipients] = useState(null);
  const [estimating, setEstimating] = useState(false);

  // AI generation
  const [showAiGen, setShowAiGen] = useState(false);
  const [aiTopic, setAiTopic] = useState("");
  const [aiTone, setAiTone] = useState("professional");
  const [aiPurpose, setAiPurpose] = useState("promotional");
  const [generating, setGenerating] = useState(false);

  // Submit
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Load tags
  useEffect(() => {
    if (!tenantId || !token) return;
    fetchTagDefinitions(tenantId, token)
      .then((res) => setAvailableTags(res.tags || res || []))
      .catch((err) => { console.warn("Tag definitions fetch failed:", err?.message); setAvailableTags([]); });
  }, [tenantId, token]);

  // Estimate recipients
  const handleEstimate = async () => {
    setEstimating(true);
    try {
      const res = await estimateCampaignRecipients(tenantId, token, {
        status: statusFilter || undefined,
        temperature: tempFilter || undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
      });
      setEstimatedRecipients(res.count ?? res.estimated_count ?? 0);
    } catch {
      setEstimatedRecipients(null);
    } finally {
      setEstimating(false);
    }
  };

  // Generate with AI
  const handleAiGenerate = async () => {
    if (!aiTopic.trim()) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await generateCampaignContent(tenantId, token, {
        topic: aiTopic.trim(),
        tone: aiTone,
        purpose: aiPurpose,
        type,
      });
      if (res.subject) setSubject(res.subject);
      if (res.body) setBody(res.body);
      if (res.content) setBody(res.content);
      setShowAiGen(false);
    } catch (e) {
      setError(e.message || "AI generation failed");
    } finally {
      setGenerating(false);
    }
  };

  // Submit campaign
  const handleSubmit = async () => {
    if (!name.trim()) { setError("Campaign name is required."); return; }
    if (type === "email" && !subject.trim()) { setError("Email subject is required."); return; }
    if (!body.trim()) { setError("Campaign body is required."); return; }

    setSubmitting(true);
    setError(null);
    try {
      const created = await createMarketingCampaign(tenantId, token, {
        name: name.trim(),
        type,
        subject: type === "email" ? subject.trim() : null,
        body: body.trim(),
        target_filter: {
          status: statusFilter ? [statusFilter] : undefined,
          lead_temperature: tempFilter ? [tempFilter] : undefined,
          tags: selectedTags.length > 0 ? selectedTags : undefined,
        },
        scheduled_for: scheduleDate && scheduleTime
          ? `${scheduleDate}T${scheduleTime}:00`
          : scheduleDate ? `${scheduleDate}T09:00:00` : null,
      });
      if (sendNow && created?.id) {
        await sendMarketingCampaign(tenantId, token, created.id);
      }
      onCreated();
    } catch (e) {
      setError(e.message || "Failed to create campaign");
    } finally {
      setSubmitting(false);
    }
  };

  const toggleTag = (tagName) => {
    setSelectedTags((prev) =>
      prev.includes(tagName) ? prev.filter((t) => t !== tagName) : [...prev, tagName]
    );
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{ ...modalStyle, maxWidth: 800 }}>
        <h2 style={{ margin: "0 0 20px", color: "var(--text-primary)", fontSize: "1.2rem" }}>
          Create Campaign
        </h2>

        {/* Campaign Name */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Campaign Name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Spring Promotion 2026"
            style={inputStyle} />
        </div>

        {/* Type Toggle */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Type</label>
          <div style={{ display: "flex", gap: 8 }}>
            {CAMPAIGN_TYPES.map((t) => (
              <button key={t.key} onClick={() => setType(t.key)} style={{
                padding: "10px 24px", borderRadius: 8, fontSize: "0.9rem", cursor: "pointer",
                border: type === t.key ? `2px solid ${t.key === "email" ? "var(--accent)" : "var(--green)"}` : "1px solid var(--border)",
                background: type === t.key ? (t.key === "email" ? "var(--accent-dim)" : "var(--green-dim)") : "var(--bg-primary)",
                color: type === t.key ? (t.key === "email" ? "var(--accent)" : "var(--green)") : "var(--text-secondary)",
                fontWeight: type === t.key ? 600 : 400,
              }}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Subject (email only) */}
        {type === "email" && (
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Subject Line</label>
            <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)}
              placeholder="Your email subject line..."
              style={inputStyle} />
          </div>
        )}

        {/* Body */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>
            {type === "email" ? "Email Body" : "SMS Message"}
          </label>
          <textarea value={body} onChange={(e) => setBody(e.target.value)}
            placeholder={type === "email" ? "Write your email content..." : "Write your SMS message..."}
            rows={type === "email" ? 8 : 3}
            maxLength={type === "sms" ? SMS_CHAR_LIMIT : undefined}
            style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", lineHeight: 1.6 }} />
          {type === "sms" && (
            <div style={{
              fontSize: "0.75rem",
              color: body.length > SMS_CHAR_LIMIT * 0.9 ? "#f87171" : "var(--text-muted)",
              marginTop: 4, textAlign: "right",
            }}>
              {body.length} / {SMS_CHAR_LIMIT}
            </div>
          )}
        </div>

        {/* AI Generate Toggle */}
        <div style={{ marginBottom: 16 }}>
          <button onClick={() => setShowAiGen(!showAiGen)} style={{
            ...btnSecondary, display: "flex", alignItems: "center", gap: 6,
          }}>
            <span style={{ fontSize: "1rem" }}>&#x2728;</span> Generate with AI
          </button>
          {showAiGen && (
            <div style={{
              marginTop: 12, padding: 16, background: "var(--bg-primary)",
              border: "1px solid var(--border)", borderRadius: 8,
            }}>
              <div style={{ marginBottom: 12 }}>
                <label style={labelStyle}>Topic</label>
                <input type="text" value={aiTopic} onChange={(e) => setAiTopic(e.target.value)}
                  placeholder="What is this campaign about?"
                  style={inputStyle} />
              </div>
              <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Tone</label>
                  <select value={aiTone} onChange={(e) => setAiTone(e.target.value)}
                    style={{ ...inputStyle, textTransform: "capitalize" }}>
                    {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Purpose</label>
                  <select value={aiPurpose} onChange={(e) => setAiPurpose(e.target.value)}
                    style={{ ...inputStyle, textTransform: "capitalize" }}>
                    {CAMPAIGN_PURPOSES.map((p) => <option key={p} value={p}>{p.replace("_", " ")}</option>)}
                  </select>
                </div>
              </div>
              <button onClick={handleAiGenerate} disabled={generating || !aiTopic.trim()}
                style={{ ...btnPrimary, opacity: generating ? 0.6 : 1, fontSize: "0.85rem", padding: "8px 16px" }}>
                {generating ? "Generating..." : "Generate Content"}
              </button>
            </div>
          )}
        </div>

        {/* Target Audience */}
        <div style={{
          marginBottom: 16, padding: 16, background: "var(--bg-primary)",
          border: "1px solid var(--border)", borderRadius: 8,
        }}>
          <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "var(--text-primary)" }}>
            Target Audience
          </h3>
          <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 140 }}>
              <label style={labelStyle}>Lead Status</label>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                style={{ ...inputStyle, textTransform: "capitalize" }}>
                <option value="">All statuses</option>
                {LEAD_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div style={{ flex: 1, minWidth: 140 }}>
              <label style={labelStyle}>Temperature</label>
              <select value={tempFilter} onChange={(e) => setTempFilter(e.target.value)}
                style={{ ...inputStyle, textTransform: "capitalize" }}>
                <option value="">All temps</option>
                {LEAD_TEMPS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>

          {/* Tags */}
          {availableTags.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle}>Tags</label>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {availableTags.map((tag) => {
                  const tagName = tag.tag_name || tag.name || tag;
                  const isSelected = selectedTags.includes(tagName);
                  return (
                    <button key={tagName} onClick={() => toggleTag(tagName)} style={{
                      padding: "4px 12px", borderRadius: 12, fontSize: "0.8rem", cursor: "pointer",
                      border: isSelected ? "2px solid var(--accent)" : "1px solid var(--border)",
                      background: isSelected ? "var(--accent-dim)" : "transparent",
                      color: isSelected ? "var(--accent)" : "var(--text-secondary)",
                      fontWeight: isSelected ? 600 : 400,
                    }}>
                      {tagName}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button onClick={handleEstimate} disabled={estimating}
              style={{ ...btnSecondary, fontSize: "0.8rem", padding: "6px 14px" }}>
              {estimating ? "Estimating..." : "Estimate Recipients"}
            </button>
            {estimatedRecipients !== null && (
              <span style={{ fontSize: "0.9rem", color: "var(--accent)", fontWeight: 600 }}>
                ~{estimatedRecipients} recipient{estimatedRecipients !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Schedule */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Schedule</label>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", color: "var(--text-secondary)", fontSize: "0.85rem" }}>
              <input type="checkbox" checked={sendNow}
                onChange={(e) => { setSendNow(e.target.checked); if (e.target.checked) { setScheduleDate(""); setScheduleTime(""); } }} />
              Send Immediately
            </label>
            {!sendNow && (
              <>
                <input type="date" value={scheduleDate} onChange={(e) => setScheduleDate(e.target.value)}
                  style={{ ...inputStyle, width: "auto" }} />
                <input type="time" value={scheduleTime} onChange={(e) => setScheduleTime(e.target.value)}
                  style={{ ...inputStyle, width: "auto" }} />
              </>
            )}
          </div>
        </div>

        {error && <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}>{error}</div>}

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>Cancel</button>
          <button onClick={handleSubmit} disabled={submitting}
            style={{ ...btnPrimary, opacity: submitting ? 0.6 : 1, cursor: submitting ? "default" : "pointer" }}>
            {submitting
              ? "Creating..."
              : sendNow
                ? "Create & Send"
                : scheduleDate
                  ? "Create & Schedule"
                  : "Save as Draft"}
          </button>
        </div>
      </div>
    </div>
  );
}
