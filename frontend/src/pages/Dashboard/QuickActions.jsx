import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { createLead } from "../../utils/api/leads";
import { createAppointment } from "../../utils/api/appointments";

const Ico = ({ d }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
);

function QuickAddLeadModal({ onClose, onSuccess }) {
  const { user, token } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", phone: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name && !form.email && !form.phone) {
      setError("Please fill in at least one field");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createLead(user.tenantId, token, {
        name: form.name || null,
        email: form.email || null,
        phone: form.phone || null,
        status: "new",
        source: "manual",
      });
      onSuccess();
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to create lead");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
        <div className="modal-header">
          <h3>Quick Add Lead</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Name</label>
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="John Smith" autoFocus />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="john@example.com" />
          </div>
          <div className="form-group">
            <label>Phone</label>
            <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="(555) 123-4567" />
          </div>
          {error && <div className="error-banner" style={{ marginBottom: "0.75rem" }}>{error}</div>}
          <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Adding..." : "Add Lead"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function QuickBookModal({ onClose, onSuccess }) {
  const { user, token } = useAuth();
  const [form, setForm] = useState({ customer_name: "", customer_email: "", customer_phone: "", date: "", time: "09:00" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.customer_name || !form.date || !form.time) {
      setError("Name, date, and time are required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const startTime = new Date(`${form.date}T${form.time}:00`).toISOString();
      const endTime = new Date(new Date(`${form.date}T${form.time}:00`).getTime() + 30 * 60000).toISOString();
      await createAppointment(user.tenantId, token, {
        customer_name: form.customer_name,
        customer_email: form.customer_email || null,
        customer_phone: form.customer_phone || null,
        start_time: startTime,
        end_time: endTime,
        status: "confirmed",
      });
      onSuccess();
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to book appointment");
    } finally {
      setSaving(false);
    }
  };

  // Default to tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const minDate = tomorrow.toISOString().split("T")[0];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
        <div className="modal-header">
          <h3>Quick Book Appointment</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Customer Name *</label>
            <input type="text" value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} placeholder="John Smith" autoFocus required />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={form.customer_email} onChange={(e) => setForm({ ...form, customer_email: e.target.value })} placeholder="john@example.com" />
          </div>
          <div className="form-group">
            <label>Phone</label>
            <input type="tel" value={form.customer_phone} onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} placeholder="(555) 123-4567" />
          </div>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Date *</label>
              <input type="date" value={form.date} min={minDate} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Time *</label>
              <input type="time" value={form.time} onChange={(e) => setForm({ ...form, time: e.target.value })} required />
            </div>
          </div>
          {error && <div className="error-banner" style={{ marginBottom: "0.75rem" }}>{error}</div>}
          <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Booking..." : "Book Appointment"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

const DEFAULT_QUICK_ACTIONS = [
  {
    label: "Quick Book",
    description: "Book an appointment now",
    action: "book",
  },
  {
    label: "Add Lead",
    description: "Manually add a new lead",
    action: "lead",
  },
  {
    label: "Send Campaign",
    description: "Blast email or SMS to leads",
    action: "campaign",
  },
  {
    label: "View Conversations",
    description: "See active customer chats",
    action: "navigate",
    page: "conversations",
  },
];

function getActionVisual(action) {
  if (action.action === "book") {
    return {
      icon: <Ico d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2z" />,
      color: "#10b981",
    };
  }
  if (action.action === "lead") {
    return {
      icon: <Ico d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM19 8v6M22 11h-6" />,
      color: "#6366f1",
    };
  }
  if (action.page === "calls") {
    return {
      icon: <Ico d="M22 16.92v3a2 2 0 0 1-2.18 2 19.86 19.86 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.86 19.86 0 0 1 2.08 4.18 2 2 0 0 1 4.06 2h3a2 2 0 0 1 2 1.72c.12.9.32 1.78.59 2.62a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.46-1.11a2 2 0 0 1 2.11-.45c.84.27 1.72.47 2.62.59A2 2 0 0 1 22 16.92z" />,
      color: "#ef4444",
    };
  }
  if (action.page === "pipeline") {
    return {
      icon: <Ico d="M3 3h7v7H3zM14 3h7v4h-7zM14 14h7v7h-7zM3 14h7v4H3zM10 6h4M17.5 7v7M10 16h4" />,
      color: "#0ea5e9",
    };
  }
  if (action.page === "calendar") {
    return {
      icon: <Ico d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2z" />,
      color: "#10b981",
    };
  }
  if (action.page === "automations") {
    return {
      icon: <Ico d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zM22 6l-10 7L2 6" />,
      color: "#f59e0b",
    };
  }
  return {
    icon: <Ico d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />,
    color: "#8b5cf6",
  };
}

export default function QuickActions({ onNavigate, businessProfile = null }) {
  const [modal, setModal] = useState(null);
  const quickActions = businessProfile?.quick_actions?.length ? businessProfile.quick_actions : DEFAULT_QUICK_ACTIONS;

  const handleAction = (action) => {
    if (action.action === "book") setModal("book");
    else if (action.action === "lead") setModal("lead");
    else if (action.action === "campaign") onNavigate("automations");
    else if (action.action === "navigate") onNavigate(action.page);
  };

  return (
    <div className="quick-actions">
      <div className="quick-actions-title">
        {businessProfile ? `${businessProfile.label} Actions` : "Quick Actions"}
      </div>
      {quickActions.map((action) => {
        const visual = getActionVisual(action);
        return (
          <div
            className="quick-action-card"
            key={action.label}
            onClick={() => handleAction(action)}
            style={{ cursor: "pointer" }}
          >
            <span className="quick-action-icon" style={{ color: visual.color }}>{visual.icon}</span>
            <div className="quick-action-body">
              <div className="quick-action-label">{action.label}</div>
              <div className="quick-action-desc">{action.description}</div>
            </div>
            <span className="quick-action-arrow">&rarr;</span>
          </div>
        );
      })}

      {modal === "lead" && (
        <QuickAddLeadModal
          onClose={() => setModal(null)}
          onSuccess={() => { setModal(null); window.location.reload(); }}
        />
      )}
      {modal === "book" && (
        <QuickBookModal
          onClose={() => setModal(null)}
          onSuccess={() => { setModal(null); window.location.reload(); }}
        />
      )}
    </div>
  );
}
