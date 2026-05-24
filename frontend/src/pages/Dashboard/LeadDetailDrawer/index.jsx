import { useState, useEffect } from "react";
import { useAuth } from "../../../context/AuthContext";
import { fetchLeadScore, assignLead } from "../../../utils/api/leads";
import { fetchTeamMembers } from "../../../utils/api/team";

import ScoreSection from "./ScoreSection";
import QualificationSection from "./QualificationSection";
import TagsAndStatusSection from "./TagsAndStatusSection";
import ContactInfoSection from "./ContactInfoSection";
import DraftDocumentSection from "./DraftDocumentSection";
import QuickFollowupSection from "./QuickFollowupSection";
import DetailsSection from "./DetailsSection";
import InsuranceSection from "./InsuranceSection";
import CustomFieldsSection from "./CustomFieldsSection";
import InfoSection from "./InfoSection";
import TimelineSection from "./TimelineSection";

const INITIAL_FORM = {
  name: "",
  email: "",
  phone: "",
  conversation_summary: "",
  status: "new",
  areas_of_interest: "",
  timeline: "",
  budget: "",
  insurance_carrier: "",
  insurance_member_id: "",
  insurance_group: "",
  date_of_birth: "",
};

export default function LeadDetailDrawer({ lead, onClose, onSave, onDelete }) {
  const { user, token } = useAuth();
  const tenantId = user?.tenantId;

  const [breakdown, setBreakdown] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [teamMembers, setTeamMembers] = useState([]);
  const [assignedTo, setAssignedTo] = useState(lead.assigned_to || "");

  useEffect(() => {
    if (!tenantId || !token) return;
    fetchTeamMembers(tenantId, token)
      .then((data) => setTeamMembers(data.members || []))
      .catch((err) => console.warn("Team members fetch failed:", err.message));
  }, [tenantId, token]);

  useEffect(() => {
    setForm({
      name: lead.name || "",
      email: lead.email || "",
      phone: lead.phone || "",
      conversation_summary: lead.conversation_summary || "",
      status: lead.status || "new",
      areas_of_interest: lead.areas_of_interest || "",
      timeline: lead.timeline || "",
      budget: lead.budget || "",
      insurance_carrier: lead.insurance_carrier || "",
      insurance_member_id: lead.insurance_member_id || "",
      insurance_group: lead.insurance_group || "",
      date_of_birth: lead.date_of_birth || "",
    });
    setConfirmDelete(false);
    setBreakdown(null);
    setAssignedTo(lead.assigned_to || "");
    if (tenantId && lead.id && token) {
      fetchLeadScore(tenantId, lead.id, token)
        .then((data) => setBreakdown(data.breakdown))
        .catch((err) => console.warn("Lead score fetch failed:", err.message));
    }
  }, [lead, tenantId, token]);

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
  };

  const handleSave = async () => {
    if (!onSave) return;
    setSaving(true);
    try {
      const updates = {};
      for (const [k, v] of Object.entries(form)) {
        const original = lead[k] || "";
        if (v !== original) updates[k] = v || null;
      }
      if (Object.keys(updates).length > 0) {
        await onSave(lead.id, updates);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    if (onDelete) await onDelete(lead.id);
  };

  const handleAssign = async (memberId) => {
    setAssignedTo(memberId);
    try {
      await assignLead(tenantId, token, lead.id, memberId || null);
    } catch (err) {
      setAssignedTo(lead.assigned_to || "");
      console.warn("Assign failed:", err.message);
    }
  };

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2 className="drawer-title">Edit Lead</h2>
          <button className="drawer-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="drawer-body">
          <ScoreSection lead={lead} breakdown={breakdown} />
          <QualificationSection lead={lead} />
          <TagsAndStatusSection lead={lead} />
          <ContactInfoSection form={form} onChange={handleChange} />
          <DraftDocumentSection
            lead={lead}
            form={form}
            tenantId={tenantId}
            token={token}
          />
          <QuickFollowupSection
            lead={lead}
            form={form}
            tenantId={tenantId}
            token={token}
          />
          <DetailsSection
            form={form}
            onChange={handleChange}
            assignedTo={assignedTo}
            onAssign={handleAssign}
            teamMembers={teamMembers}
          />
          <InsuranceSection form={form} lead={lead} onChange={handleChange} />
          <CustomFieldsSection lead={lead} tenantId={tenantId} token={token} />
          <InfoSection lead={lead} />
          <TimelineSection lead={lead} tenantId={tenantId} token={token} />
        </div>
        <div className="drawer-footer">
          <button
            className={`drawer-btn drawer-btn-danger${
              confirmDelete ? " confirming" : ""
            }`}
            onClick={handleDelete}
          >
            {confirmDelete ? "Confirm Delete" : "Delete"}
          </button>
          <button
            className="drawer-btn drawer-btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
