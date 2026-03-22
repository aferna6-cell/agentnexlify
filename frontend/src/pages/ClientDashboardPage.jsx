import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

export default function ClientDashboardPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    const token = sessionStorage.getItem(`client_token_${slug}`);
    if (!token) {
      navigate(`/client/login/${slug}`);
      return;
    }
    fetch(`${API_BASE}/api/v1/portal/client/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (res.status === 401) {
          sessionStorage.removeItem(`client_token_${slug}`);
          navigate(`/client/login/${slug}`);
          return null;
        }
        if (!res.ok) throw new Error("Failed to load portal data");
        return res.json();
      })
      .then((d) => { if (d) setData(d); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [slug, navigate]);

  const handleLogout = () => {
    sessionStorage.removeItem(`client_token_${slug}`);
    navigate(`/client/login/${slug}`);
  };

  if (loading) return <div style={s.wrapper}><div style={s.loader} /></div>;
  if (error) return <div style={s.wrapper}><div style={s.errorCard}>{error}</div></div>;
  if (!data) return null;

  const { business, customer, service_records, appointments, invoices, documents } = data;

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "appointments", label: `Appointments (${appointments?.length || 0})` },
    { id: "invoices", label: `Invoices (${invoices?.length || 0})` },
    { id: "services", label: `Service History (${service_records?.length || 0})` },
    { id: "documents", label: `Documents (${documents?.length || 0})` },
  ];

  return (
    <div style={s.wrapper}>
      <div style={s.container}>
        {/* Header */}
        <div style={s.header}>
          <div>
            <h1 style={s.businessName}>{business?.business_name || "Client Portal"}</h1>
            <p style={s.welcome}>Welcome back, {customer?.name || customer?.email || "Client"}</p>
          </div>
          <button style={s.logoutBtn} onClick={handleLogout}>Sign Out</button>
        </div>

        {/* Tabs */}
        <div style={s.tabBar}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              style={activeTab === tab.id ? { ...s.tab, ...s.tabActive } : s.tab}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div style={s.content}>
          {activeTab === "overview" && <OverviewTab data={data} />}
          {activeTab === "appointments" && <AppointmentsTab items={appointments || []} />}
          {activeTab === "invoices" && <InvoicesTab items={invoices || []} />}
          {activeTab === "services" && <ServicesTab items={service_records || []} />}
          {activeTab === "documents" && <DocumentsTab items={documents || []} />}
        </div>
      </div>
    </div>
  );
}

function OverviewTab({ data }) {
  const { appointments, invoices, service_records, documents, rebook_enabled } = data;
  const upcoming = (appointments || []).filter(
    (a) => a.status === "confirmed" && new Date(a.start_time) > new Date()
  );
  const unpaid = (invoices || []).filter((i) => i.status === "sent" || i.status === "overdue");
  const pendingDocs = (documents || []).filter((d) => d.status === "sent");

  return (
    <div>
      <div style={s.statsRow}>
        <StatCard label="Upcoming Appointments" value={upcoming.length} color="#6366f1" />
        <StatCard label="Unpaid Invoices" value={unpaid.length} color={unpaid.length > 0 ? "#f59e0b" : "#10b981"} />
        <StatCard label="Service Records" value={(service_records || []).length} color="#8b5cf6" />
        <StatCard label="Pending Signatures" value={pendingDocs.length} color={pendingDocs.length > 0 ? "#f59e0b" : "#10b981"} />
      </div>

      {upcoming.length > 0 && (
        <div style={s.section}>
          <h3 style={s.sectionTitle}>Upcoming Appointments</h3>
          {upcoming.slice(0, 3).map((a) => (
            <div key={a.id} style={s.listItem}>
              <span style={s.itemTitle}>{a.customer_name || "Appointment"}</span>
              <span style={s.itemMeta}>{new Date(a.start_time).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}

      {unpaid.length > 0 && (
        <div style={s.section}>
          <h3 style={s.sectionTitle}>Outstanding Invoices</h3>
          {unpaid.slice(0, 3).map((inv) => (
            <div key={inv.id} style={s.listItem}>
              <span style={s.itemTitle}>Invoice #{inv.invoice_number}</span>
              <span style={{ ...s.itemMeta, color: "#f59e0b" }}>${Number(inv.total || 0).toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div style={s.statCard}>
      <div style={{ ...s.statValue, color }}>{value}</div>
      <div style={s.statLabel}>{label}</div>
    </div>
  );
}

function AppointmentsTab({ items }) {
  if (!items.length) return <EmptyState text="No appointments yet." />;
  return (
    <div>
      {items.map((a) => (
        <div key={a.id} style={s.card}>
          <div style={s.cardRow}>
            <span style={s.cardTitle}>{a.customer_name || "Appointment"}</span>
            <StatusBadge status={a.status} />
          </div>
          <div style={s.cardMeta}>
            {new Date(a.start_time).toLocaleDateString()} at{" "}
            {new Date(a.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            {" — "}
            {new Date(a.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </div>
          {a.notes && <div style={s.cardNotes}>{a.notes}</div>}
        </div>
      ))}
    </div>
  );
}

function InvoicesTab({ items }) {
  if (!items.length) return <EmptyState text="No invoices yet." />;
  return (
    <div>
      {items.map((inv) => (
        <div key={inv.id} style={s.card}>
          <div style={s.cardRow}>
            <span style={s.cardTitle}>Invoice #{inv.invoice_number}</span>
            <StatusBadge status={inv.status} />
          </div>
          <div style={s.cardMeta}>
            Total: ${Number(inv.total || 0).toFixed(2)}
            {inv.due_date && ` — Due: ${new Date(inv.due_date).toLocaleDateString()}`}
          </div>
          {inv.items_json && Array.isArray(inv.items_json) && (
            <div style={{ marginTop: 8 }}>
              {inv.items_json.map((item, i) => (
                <div key={i} style={s.invoiceItem}>
                  <span>{item.description || item.name}</span>
                  <span>${Number(item.total || item.amount || 0).toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ServicesTab({ items }) {
  if (!items.length) return <EmptyState text="No service records yet." />;
  return (
    <div>
      {items.map((rec) => (
        <div key={rec.id} style={s.card}>
          <div style={s.cardRow}>
            <span style={s.cardTitle}>{rec.title}</span>
            {rec.invoice_amount && (
              <span style={{ color: "#10b981", fontWeight: 600 }}>
                ${Number(rec.invoice_amount).toFixed(2)}
              </span>
            )}
          </div>
          {rec.service_date && (
            <div style={s.cardMeta}>{new Date(rec.service_date).toLocaleDateString()}</div>
          )}
          {rec.description && <div style={s.cardNotes}>{rec.description}</div>}
        </div>
      ))}
    </div>
  );
}

function DocumentsTab({ items }) {
  if (!items.length) return <EmptyState text="No documents yet." />;
  return (
    <div>
      {items.map((doc) => (
        <div key={doc.id} style={s.card}>
          <div style={s.cardRow}>
            <span style={s.cardTitle}>{doc.title}</span>
            <StatusBadge status={doc.status} />
          </div>
          <div style={s.cardMeta}>
            Created: {new Date(doc.created_at).toLocaleDateString()}
            {doc.signed_at && ` — Signed: ${new Date(doc.signed_at).toLocaleDateString()}`}
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    confirmed: { bg: "rgba(99,102,241,0.15)", text: "#a5b4fc" },
    completed: { bg: "rgba(16,185,129,0.15)", text: "#6ee7b7" },
    cancelled: { bg: "rgba(239,68,68,0.15)", text: "#fca5a5" },
    no_show: { bg: "rgba(239,68,68,0.15)", text: "#fca5a5" },
    sent: { bg: "rgba(245,158,11,0.15)", text: "#fcd34d" },
    paid: { bg: "rgba(16,185,129,0.15)", text: "#6ee7b7" },
    overdue: { bg: "rgba(239,68,68,0.15)", text: "#fca5a5" },
    draft: { bg: "rgba(255,255,255,0.08)", text: "rgba(255,255,255,0.5)" },
    signed: { bg: "rgba(16,185,129,0.15)", text: "#6ee7b7" },
  };
  const c = colors[status] || colors.draft;
  return (
    <span style={{ background: c.bg, color: c.text, fontSize: 12, fontWeight: 500, padding: "3px 10px", borderRadius: 8 }}>
      {status}
    </span>
  );
}

function EmptyState({ text }) {
  return (
    <div style={{ textAlign: "center", padding: "60px 20px", color: "rgba(255,255,255,0.4)" }}>
      <div style={{ fontSize: 40, marginBottom: 12 }}>-</div>
      <p>{text}</p>
    </div>
  );
}

const s = {
  wrapper: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
    fontFamily: "'Inter', -apple-system, sans-serif",
    padding: "20px",
    color: "#fff",
  },
  container: { maxWidth: 900, margin: "0 auto" },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
    flexWrap: "wrap",
    gap: 12,
  },
  businessName: { fontSize: 24, fontWeight: 700, margin: 0, color: "#fff" },
  welcome: { color: "rgba(255,255,255,0.5)", fontSize: 14, margin: "4px 0 0" },
  logoutBtn: {
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 8,
    color: "rgba(255,255,255,0.6)",
    padding: "8px 16px",
    fontSize: 13,
    cursor: "pointer",
  },
  tabBar: {
    display: "flex",
    gap: 4,
    borderBottom: "1px solid rgba(255,255,255,0.08)",
    marginBottom: 24,
    overflowX: "auto",
  },
  tab: {
    background: "none",
    border: "none",
    color: "rgba(255,255,255,0.4)",
    fontSize: 13,
    fontWeight: 500,
    padding: "10px 16px",
    cursor: "pointer",
    borderBottom: "2px solid transparent",
    whiteSpace: "nowrap",
  },
  tabActive: {
    color: "#a5b4fc",
    borderBottomColor: "#6366f1",
  },
  content: { minHeight: 300 },
  statsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: 16,
    marginBottom: 32,
  },
  statCard: {
    background: "rgba(30, 27, 75, 0.5)",
    border: "1px solid rgba(99,102,241,0.15)",
    borderRadius: 12,
    padding: "20px",
    textAlign: "center",
  },
  statValue: { fontSize: 28, fontWeight: 700 },
  statLabel: { color: "rgba(255,255,255,0.5)", fontSize: 12, marginTop: 4 },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 16, fontWeight: 600, margin: "0 0 12px", color: "rgba(255,255,255,0.8)" },
  listItem: {
    display: "flex",
    justifyContent: "space-between",
    padding: "10px 14px",
    background: "rgba(30,27,75,0.3)",
    borderRadius: 8,
    marginBottom: 6,
  },
  itemTitle: { fontWeight: 500, fontSize: 14 },
  itemMeta: { color: "rgba(255,255,255,0.5)", fontSize: 13 },
  card: {
    background: "rgba(30,27,75,0.5)",
    border: "1px solid rgba(99,102,241,0.12)",
    borderRadius: 12,
    padding: "16px 20px",
    marginBottom: 12,
  },
  cardRow: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  cardTitle: { fontWeight: 600, fontSize: 15 },
  cardMeta: { color: "rgba(255,255,255,0.5)", fontSize: 13, marginTop: 6 },
  cardNotes: { color: "rgba(255,255,255,0.4)", fontSize: 13, marginTop: 8, lineHeight: 1.5 },
  invoiceItem: {
    display: "flex",
    justifyContent: "space-between",
    padding: "4px 0",
    borderBottom: "1px solid rgba(255,255,255,0.05)",
    fontSize: 13,
    color: "rgba(255,255,255,0.6)",
  },
  loader: {
    width: 36,
    height: 36,
    border: "3px solid rgba(255,255,255,0.1)",
    borderTopColor: "#6366f1",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
    margin: "40vh auto",
  },
  errorCard: {
    background: "rgba(239,68,68,0.1)",
    border: "1px solid rgba(239,68,68,0.3)",
    borderRadius: 12,
    padding: 24,
    color: "#fca5a5",
    textAlign: "center",
    maxWidth: 400,
    margin: "30vh auto",
  },
};
