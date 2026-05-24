import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import SkeletonLoader from "../../components/SkeletonLoader";
import {
  fetchForms,
  createForm,
  updateForm,
  deleteForm,
  fetchFormSubmissions,
  fetchFormStats,
} from "../../utils/api/forms";
import { emptyFormData, newEmptyField } from "./utils";
import FormEditor from "./FormEditor";
import SubmissionsView from "./SubmissionsView";
import FormsGrid from "./FormsGrid";

export default function FormBuilderPage() {
  const { user, token } = useAuth();
  const [forms, setForms] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showEditor, setShowEditor] = useState(false);
  const [editingForm, setEditingForm] = useState(null);
  const [formData, setFormData] = useState({ ...emptyFormData, fields: [] });
  const [saving, setSaving] = useState(false);

  const [viewingSubmissions, setViewingSubmissions] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [loadingSubs, setLoadingSubs] = useState(false);
  const [expandedSubId, setExpandedSubId] = useState(null);

  const [copiedEmbed, setCopiedEmbed] = useState(null);
  const [deletingIds, setDeletingIds] = useState(new Set());

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const [formsData, statsData] = await Promise.all([
        fetchForms(user.tenantId, token),
        fetchFormStats(user.tenantId, token),
      ]);
      setForms(formsData.forms || formsData || []);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.warn("Failed to load forms:", err.message);
      setError(err.message || "Failed to load forms");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditingForm(null);
    setFormData({
      name: "",
      description: "",
      fields: [
        {
          id: "field_1",
          type: "text",
          label: "Your Name",
          placeholder: "John Doe",
          required: true,
          options: [],
        },
        {
          id: "field_2",
          type: "email",
          label: "Email",
          placeholder: "you@example.com",
          required: true,
          options: [],
        },
        {
          id: "field_3",
          type: "textarea",
          label: "Message",
          placeholder: "How can we help?",
          required: false,
          options: [],
        },
      ],
      settings: {
        success_message: "Thank you for your submission!",
        redirect_url: "",
        is_active: true,
      },
    });
    setShowEditor(true);
  };

  const openEdit = (form) => {
    setEditingForm(form);
    const fields = (form.fields_json || []).map((f) => ({
      ...f,
      options: f.options || [],
      placeholder: f.placeholder || "",
      required: f.required || false,
    }));
    setFormData({
      name: form.name || "",
      description: form.description || "",
      fields,
      settings: form.settings_json || {
        success_message: "Thank you for your submission!",
        redirect_url: "",
        is_active: true,
      },
    });
    setShowEditor(true);
  };

  const addField = () => {
    setFormData((prev) => ({
      ...prev,
      fields: [...prev.fields, newEmptyField(prev.fields)],
    }));
  };

  const removeField = (idx) => {
    setFormData((prev) => ({
      ...prev,
      fields: prev.fields.filter((_, i) => i !== idx),
    }));
  };

  const updateField = (idx, key, value) => {
    setFormData((prev) => ({
      ...prev,
      fields: prev.fields.map((f, i) =>
        i === idx ? { ...f, [key]: value } : f,
      ),
    }));
  };

  const moveField = (idx, direction) => {
    const targetIdx = idx + direction;
    if (targetIdx < 0 || targetIdx >= formData.fields.length) return;
    setFormData((prev) => {
      const next = [...prev.fields];
      [next[idx], next[targetIdx]] = [next[targetIdx], next[idx]];
      return { ...prev, fields: next };
    });
  };

  const updateSettings = (key, value) => {
    setFormData((prev) => ({
      ...prev,
      settings: { ...prev.settings, [key]: value },
    }));
  };

  const handleSave = async () => {
    if (!formData.name.trim()) return;
    if (formData.fields.length === 0) {
      setError("Add at least one field to your form");
      return;
    }
    setSaving(true);
    const body = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      fields_json: formData.fields.map((f) => ({
        id: f.id,
        type: f.type,
        label: f.label,
        placeholder: f.placeholder || undefined,
        required: f.required,
        options: ["select", "radio", "checkbox"].includes(f.type)
          ? f.options
          : undefined,
      })),
      settings_json: formData.settings,
    };

    try {
      if (editingForm) {
        await updateForm(user.tenantId, token, editingForm.id, body);
      } else {
        await createForm(user.tenantId, token, body);
      }
      setShowEditor(false);
      setEditingForm(null);
      setFormData({ ...emptyFormData, fields: [] });
      loadData();
    } catch (err) {
      console.warn("Save form failed:", err.message);
      setError(err.message || "Failed to save form");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (formId) => {
    if (
      !window.confirm(
        "Delete this form? This cannot be undone. All submissions will also be deleted.",
      )
    )
      return;
    setDeletingIds((prev) => new Set(prev).add(formId));
    try {
      await deleteForm(user.tenantId, token, formId);
      setForms((prev) => prev.filter((f) => f.id !== formId));
      if (viewingSubmissions?.id === formId) setViewingSubmissions(null);
      setError(null);
    } catch (err) {
      console.warn("Delete form failed:", err.message);
      setError(err.message || "Failed to delete form");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(formId);
        return next;
      });
    }
  };

  const openSubmissions = async (form) => {
    setViewingSubmissions(form);
    setLoadingSubs(true);
    setExpandedSubId(null);
    try {
      const data = await fetchFormSubmissions(user.tenantId, token, form.id);
      setSubmissions(data.submissions || data || []);
    } catch (err) {
      console.warn("Failed to load submissions:", err.message);
      setSubmissions([]);
    } finally {
      setLoadingSubs(false);
    }
  };

  const copyToClipboard = (text, type) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopiedEmbed(type);
        setTimeout(() => setCopiedEmbed(null), 2000);
      })
      .catch(() => {
        setError("Failed to copy to clipboard");
      });
  };

  const totalForms = stats?.total_forms ?? forms.length;
  const totalSubmissions = stats?.total_submissions ?? 0;
  const activeForms =
    stats?.active_forms ?? forms.filter((f) => f.is_active !== false).length;
  const conversionRate = stats?.conversion_rate ?? 0;

  if (loading) return <SkeletonLoader />;

  if (viewingSubmissions) {
    return (
      <SubmissionsView
        viewingSubmissions={viewingSubmissions}
        submissions={submissions}
        loadingSubs={loadingSubs}
        expandedSubId={expandedSubId}
        setExpandedSubId={setExpandedSubId}
        setViewingSubmissions={setViewingSubmissions}
        copyToClipboard={copyToClipboard}
        copiedEmbed={copiedEmbed}
      />
    );
  }

  if (showEditor) {
    return (
      <FormEditor
        formData={formData}
        setFormData={setFormData}
        editingForm={editingForm}
        saving={saving}
        error={error}
        setError={setError}
        setShowEditor={setShowEditor}
        setEditingForm={setEditingForm}
        handleSave={handleSave}
        addField={addField}
        removeField={removeField}
        updateField={updateField}
        moveField={moveField}
        updateSettings={updateSettings}
        copyToClipboard={copyToClipboard}
        copiedEmbed={copiedEmbed}
      />
    );
  }

  return (
    <FormsGrid
      forms={forms}
      totalForms={totalForms}
      totalSubmissions={totalSubmissions}
      activeForms={activeForms}
      conversionRate={conversionRate}
      error={error}
      setError={setError}
      setLoading={setLoading}
      loadData={loadData}
      openCreate={openCreate}
      openEdit={openEdit}
      openSubmissions={openSubmissions}
      copyToClipboard={copyToClipboard}
      copiedEmbed={copiedEmbed}
      handleDelete={handleDelete}
      deletingIds={deletingIds}
    />
  );
}
