import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchFaqEntries, createFaqEntry, updateFaqEntry, deleteFaqEntry } from "../utils/api/faq";
import SkeletonLoader from "../components/SkeletonLoader";

export default function FaqManagerPage() {
  const { user, token } = useAuth();
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ question: "", answer: "", category: "" });
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ question: "", answer: "", category: "" });

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const data = await fetchFaqEntries(user.tenantId, token);
      setFaqs(data || []);
    } catch (err) {
      console.error("Failed to load FAQs", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!form.question.trim() || !form.answer.trim()) return;
    setSaving(true);
    try {
      const entry = await createFaqEntry(user.tenantId, token, form);
      setFaqs((prev) => [...prev, entry]);
      setForm({ question: "", answer: "", category: "" });
      setShowForm(false);
    } catch (err) {
      console.error("Failed to create FAQ", err);
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (faq) => {
    setEditingId(faq.id);
    setEditForm({ question: faq.question, answer: faq.answer, category: faq.category || "" });
  };

  const handleUpdate = async () => {
    if (!editForm.question.trim() || !editForm.answer.trim()) return;
    setSaving(true);
    try {
      const updated = await updateFaqEntry(user.tenantId, token, editingId, editForm);
      setFaqs((prev) => prev.map((f) => (f.id === editingId ? { ...f, ...updated } : f)));
      setEditingId(null);
    } catch (err) {
      console.error("Failed to update FAQ", err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (faqId) => {
    if (deleteConfirm !== faqId) {
      setDeleteConfirm(faqId);
      return;
    }
    try {
      await deleteFaqEntry(user.tenantId, token, faqId);
      setFaqs((prev) => prev.filter((f) => f.id !== faqId));
      setDeleteConfirm(null);
    } catch (err) {
      console.error("Failed to delete FAQ", err);
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>FAQ Manager</h1>
        <p>Manage the knowledge base your AI widget uses to answer questions</p>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "+ Add FAQ"}
        </button>
      </div>

      {showForm && (
        <div className="settings-card" style={{ marginBottom: "1rem" }}>
          <h3>New FAQ Entry</h3>
          <div className="settings-field">
            <label>Question</label>
            <input
              value={form.question}
              onChange={(e) => setForm((f) => ({ ...f, question: e.target.value }))}
              placeholder="What are your business hours?"
            />
          </div>
          <div className="settings-field">
            <label>Answer</label>
            <textarea
              value={form.answer}
              onChange={(e) => setForm((f) => ({ ...f, answer: e.target.value }))}
              placeholder="We are open Monday to Friday, 9am to 5pm."
              rows={3}
            />
          </div>
          <div className="settings-field">
            <label>Category (optional)</label>
            <input
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
              placeholder="General"
            />
          </div>
          <button className="btn-primary" onClick={handleCreate} disabled={saving || !form.question.trim() || !form.answer.trim()}>
            {saving ? "Saving..." : "Save FAQ"}
          </button>
        </div>
      )}

      {faqs.length === 0 && !showForm ? (
        <div className="empty-card">
          <p>No FAQ entries yet. Add questions and answers that your AI widget can use to help visitors.</p>
        </div>
      ) : (
        <div className="faq-list">
          {faqs.map((faq) => (
            <div key={faq.id} className="faq-item">
              {editingId === faq.id ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", width: "100%" }}>
                  <input
                    value={editForm.question}
                    onChange={(e) => setEditForm((f) => ({ ...f, question: e.target.value }))}
                    style={{ width: "100%" }}
                  />
                  <textarea
                    value={editForm.answer}
                    onChange={(e) => setEditForm((f) => ({ ...f, answer: e.target.value }))}
                    rows={3}
                    style={{ width: "100%" }}
                  />
                  <input
                    value={editForm.category}
                    onChange={(e) => setEditForm((f) => ({ ...f, category: e.target.value }))}
                    placeholder="Category"
                    style={{ width: "100%" }}
                  />
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button className="btn-primary" onClick={handleUpdate} disabled={saving}>
                      {saving ? "Saving..." : "Save"}
                    </button>
                    <button className="faq-delete-btn" onClick={() => setEditingId(null)}>Cancel</button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="faq-item-q">{faq.question}</div>
                  <div className="faq-item-a">{faq.answer}</div>
                  {faq.category && <div className="faq-item-cat">{faq.category}</div>}
                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                    <button className="btn-primary" onClick={() => startEdit(faq)} style={{ fontSize: "0.8rem", padding: "4px 12px" }}>
                      Edit
                    </button>
                    <button
                      className={`faq-delete-btn${deleteConfirm === faq.id ? " confirming" : ""}`}
                      onClick={() => handleDelete(faq.id)}
                    >
                      {deleteConfirm === faq.id ? "Confirm Delete" : "Delete"}
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
