import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import SkeletonLoader from "../../components/SkeletonLoader";
import {
  fetchBids,
  createBid,
  updateBid,
  deleteBid,
  updateBidStatus,
  fetchBidStats,
  fetchBidTemplates,
  createBidTemplate,
  deleteBidTemplate,
  aiGenerateBid,
} from "../../utils/api/bids";
import { emptyLineItem, emptyForm } from "./utils";
import BidsList from "./BidsList";
import BidDetailModal from "./BidDetailModal";
import BidEditorModal from "./BidEditorModal";
import TemplatesModal from "./TemplatesModal";

export default function BidsPage() {
  const { user, token } = useAuth();
  const [bids, setBids] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [activeFilter, setActiveFilter] = useState("all");

  const [showModal, setShowModal] = useState(false);
  const [editBid, setEditBid] = useState(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  const [detailBid, setDetailBid] = useState(null);

  const [aiPrompt, setAiPrompt] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);

  const [showTemplates, setShowTemplates] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);

  const [deletingIds, setDeletingIds] = useState(new Set());

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const params = {};
      if (activeFilter !== "all") params.status = activeFilter;
      const [bidsData, statsData] = await Promise.all([
        fetchBids(user.tenantId, token, params),
        fetchBidStats(user.tenantId, token),
      ]);
      setBids(bidsData.bids || bidsData || []);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.warn("Failed to load bids:", err.message);
      setError(err.message || "Failed to load bids");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, activeFilter]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const loadTemplates = async () => {
    if (!user?.tenantId) return;
    setTemplatesLoading(true);
    try {
      const data = await fetchBidTemplates(user.tenantId, token);
      setTemplates(data.templates || data || []);
    } catch (err) {
      console.warn("Failed to load templates:", err.message);
    } finally {
      setTemplatesLoading(false);
    }
  };

  const openCreate = () => {
    setEditBid(null);
    setForm({ ...emptyForm, line_items: [{ ...emptyLineItem }] });
    setAiPrompt("");
    setShowModal(true);
  };

  const openEdit = (bid) => {
    setEditBid(bid);
    setForm({
      title: bid.title || "",
      description: bid.description || "",
      line_items:
        bid.line_items && bid.line_items.length > 0
          ? bid.line_items.map((li) => ({ ...li }))
          : [{ ...emptyLineItem }],
      terms: bid.terms || "",
      timeline: bid.timeline || "",
    });
    setShowModal(true);
    setDetailBid(null);
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    const body = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      line_items: form.line_items.filter((li) => li.name.trim()),
      terms: form.terms.trim() || null,
      timeline: form.timeline.trim() || null,
    };
    try {
      if (editBid) {
        await updateBid(user.tenantId, token, editBid.id, body);
      } else {
        await createBid(user.tenantId, token, body);
      }
      setShowModal(false);
      setForm({ ...emptyForm });
      setEditBid(null);
      loadData();
    } catch (err) {
      console.warn("Save bid failed:", err.message);
      setError(err.message || "Failed to save bid");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (bidId) => {
    if (!window.confirm("Delete this bid? This cannot be undone.")) return;
    setDeletingIds((prev) => new Set(prev).add(bidId));
    try {
      await deleteBid(user.tenantId, token, bidId);
      setBids((prev) => prev.filter((b) => b.id !== bidId));
      if (detailBid && detailBid.id === bidId) setDetailBid(null);
      setError(null);
    } catch (err) {
      console.warn("Delete bid failed:", err.message);
      setError(err.message || "Failed to delete bid");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(bidId);
        return next;
      });
    }
  };

  const handleStatusChange = async (bidId, newStatus) => {
    try {
      await updateBidStatus(user.tenantId, token, bidId, newStatus);
      setBids((prev) =>
        prev.map((b) => (b.id === bidId ? { ...b, status: newStatus } : b)),
      );
      if (detailBid && detailBid.id === bidId) {
        setDetailBid((prev) => ({ ...prev, status: newStatus }));
      }
    } catch (err) {
      console.warn("Status update failed:", err.message);
      setError(err.message || "Failed to update status");
    }
  };

  const handleAiGenerate = async () => {
    if (!aiPrompt.trim()) return;
    setAiGenerating(true);
    try {
      const result = await aiGenerateBid(user.tenantId, token, aiPrompt.trim());
      setForm({
        title: result.title || "",
        description: result.description || "",
        line_items:
          result.line_items && result.line_items.length > 0
            ? result.line_items
            : [{ ...emptyLineItem }],
        terms: result.terms || "",
        timeline: result.timeline || "",
      });
      setAiPrompt("");
    } catch (err) {
      console.warn("AI generate failed:", err.message);
      setError(err.message || "AI generation failed");
    } finally {
      setAiGenerating(false);
    }
  };

  const handleSaveAsTemplate = async (bid) => {
    setSavingTemplate(true);
    try {
      await createBidTemplate(user.tenantId, token, {
        name: bid.title,
        line_items: bid.line_items || [],
        terms: bid.terms || "",
        timeline: bid.timeline || "",
        description: bid.description || "",
      });
      if (showTemplates) loadTemplates();
    } catch (err) {
      console.warn("Save template failed:", err.message);
      setError(err.message || "Failed to save template");
    } finally {
      setSavingTemplate(false);
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm("Delete this template?")) return;
    try {
      await deleteBidTemplate(user.tenantId, token, templateId);
      setTemplates((prev) => prev.filter((t) => t.id !== templateId));
    } catch (err) {
      console.warn("Delete template failed:", err.message);
    }
  };

  const handleUseTemplate = (template) => {
    setForm({
      title: template.name || "",
      description: template.description || "",
      line_items:
        template.line_items && template.line_items.length > 0
          ? template.line_items.map((li) => ({ ...li }))
          : [{ ...emptyLineItem }],
      terms: template.terms || "",
      timeline: template.timeline || "",
    });
    setShowTemplates(false);
    if (!showModal) {
      setEditBid(null);
      setShowModal(true);
    }
  };

  const addLineItem = () => {
    setForm((f) => ({
      ...f,
      line_items: [...f.line_items, { ...emptyLineItem }],
    }));
  };

  const removeLineItem = (idx) => {
    setForm((f) => ({
      ...f,
      line_items:
        f.line_items.length > 1
          ? f.line_items.filter((_, i) => i !== idx)
          : f.line_items,
    }));
  };

  const updateLineItem = (idx, field, value) => {
    setForm((f) => ({
      ...f,
      line_items: f.line_items.map((li, i) =>
        i === idx ? { ...li, [field]: value } : li,
      ),
    }));
  };

  if (loading) return <SkeletonLoader />;

  return (
    <>
      <BidsList
        bids={bids}
        stats={stats}
        activeFilter={activeFilter}
        setActiveFilter={setActiveFilter}
        error={error}
        setError={setError}
        setLoading={setLoading}
        loadData={loadData}
        openCreate={openCreate}
        openEdit={openEdit}
        setDetailBid={setDetailBid}
        handleDelete={handleDelete}
        deletingIds={deletingIds}
        setShowTemplates={setShowTemplates}
        loadTemplates={loadTemplates}
      />
      <BidDetailModal
        detailBid={detailBid}
        setDetailBid={setDetailBid}
        openEdit={openEdit}
        handleStatusChange={handleStatusChange}
        handleSaveAsTemplate={handleSaveAsTemplate}
        savingTemplate={savingTemplate}
      />
      <BidEditorModal
        showModal={showModal}
        setShowModal={setShowModal}
        editBid={editBid}
        setEditBid={setEditBid}
        form={form}
        setForm={setForm}
        saving={saving}
        handleSave={handleSave}
        aiPrompt={aiPrompt}
        setAiPrompt={setAiPrompt}
        aiGenerating={aiGenerating}
        handleAiGenerate={handleAiGenerate}
        addLineItem={addLineItem}
        removeLineItem={removeLineItem}
        updateLineItem={updateLineItem}
      />
      <TemplatesModal
        showTemplates={showTemplates}
        setShowTemplates={setShowTemplates}
        templates={templates}
        templatesLoading={templatesLoading}
        handleUseTemplate={handleUseTemplate}
        handleDeleteTemplate={handleDeleteTemplate}
      />
    </>
  );
}
