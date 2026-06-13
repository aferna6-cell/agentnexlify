import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { notify } from "../utils/notify";
import {
  fetchTenant,
  updateTenantSettings,
  fetchKnowledgeStats,
} from "../utils/api/dashboard";
import {
  fetchAiFeedback,
  deleteAiFeedback,
  startWebsiteCrawl,
  getCrawlStatus,
} from "../utils/api/widget-config";
import {
  fetchTagDefinitions,
  createTagDefinition,
  updateTagDefinition,
  deleteTagDefinition,
} from "../utils/api/tags";
import {
  searchAvailableNumbers,
  provisionPhoneNumber,
  releasePhoneNumber,
} from "../utils/api/phone";
import {
  fetchFieldDefinitions,
  createFieldDefinition,
  deleteFieldDefinition,
} from "../utils/api/misc";
import { toggleClientLogin } from "../utils/api/portal";
import SkeletonLoader from "../components/SkeletonLoader";
import SettingsPageContent from "./settings/SettingsPageContent";

export default function SettingsPage({ onNavigate }) {
  const apiBase =
    import.meta.env.VITE_API_BASE_URL ||
    "https://agentnexlify-production.up.railway.app";
  const { user, token, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [form, setForm] = useState({
    business_name: "",
    business_type: "",
    city: "",
    owner_name: "",
    notification_phone: "",
    sms_notifications_enabled: false,
    conversation_notify_email: "",
    conversation_email_notify_enabled: false,
    google_review_link: "",
    review_request_config: { enabled: false, delay_hours: 24, method: "email" },
    daily_briefing_enabled: false,
    noshow_recovery_enabled: true,
    os_auto_send_enabled: false,
    os_auto_send_rules: {},
    voice_ai_enabled: false,
    website_url: "",
    textback_enabled: false,
    textback_message:
      "Hi! Sorry we missed your call at {business_name}. How can we help? Reply here and we'll get back to you right away.",
    textback_quiet_start: "22:00",
    textback_quiet_end: "08:00",
  });
  const [email, setEmail] = useState("");
  const [livePlan, setLivePlan] = useState(user?.plan || "free");
  const [feedback, setFeedback] = useState([]);
  const [knowledgeStats, setKnowledgeStats] = useState(null);
  const [crawlStatus, setCrawlStatus] = useState(null);
  const [crawling, setCrawling] = useState(false);
  const [businessSlug, setBusinessSlug] = useState(null);
  const [businessPageEnabled, setBusinessPageEnabled] = useState(false);
  const [clientLoginEnabled, setClientLoginEnabled] = useState(false);
  const [togglingClientLogin, setTogglingClientLogin] = useState(false);
  const [tagDefs, setTagDefs] = useState([]);
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState("#6b7280");
  const [savingTag, setSavingTag] = useState(false);

  const [customFieldDefs, setCustomFieldDefs] = useState([]);
  const [cfLoadError, setCfLoadError] = useState(null);
  const [newFieldName, setNewFieldName] = useState("");
  const [newFieldType, setNewFieldType] = useState("text");
  const [newFieldOptions, setNewFieldOptions] = useState("");
  const [newFieldRequired, setNewFieldRequired] = useState(false);
  const [savingField, setSavingField] = useState(false);
  const [deletingFieldId, setDeletingFieldId] = useState(null);

  const [provisionedPhone, setProvisionedPhone] = useState(null);
  const [phoneAreaCode, setPhoneAreaCode] = useState("");
  const [availableNumbers, setAvailableNumbers] = useState([]);
  const [searchingNumbers, setSearchingNumbers] = useState(false);
  const [provisioningPhone, setProvisioningPhone] = useState(false);
  const [releasingPhone, setReleasingPhone] = useState(false);
  const [phoneError, setPhoneError] = useState(null);
  const [phoneSuccess, setPhoneSuccess] = useState(null);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const tenant = await fetchTenant(user.tenantId, token);
      setForm({
        business_name: tenant.business_name || "",
        business_type: tenant.business_type || "",
        city: tenant.city || "",
        owner_name: tenant.owner_name || "",
        notification_phone: tenant.notification_phone || "",
        sms_notifications_enabled: tenant.sms_notifications_enabled || false,
        conversation_notify_email: tenant.conversation_notify_email || "",
        conversation_email_notify_enabled:
          tenant.conversation_email_notify_enabled || false,
        google_review_link: tenant.google_review_link || "",
        review_request_config: tenant.review_request_config || {
          enabled: false,
          delay_hours: 24,
          method: "email",
        },
        daily_briefing_enabled: tenant.daily_briefing_enabled || false,
        noshow_recovery_enabled: tenant.noshow_recovery_enabled !== false,
        os_auto_send_enabled: tenant.os_auto_send_enabled || false,
        os_auto_send_rules: tenant.os_auto_send_rules || {},
        voice_ai_enabled: tenant.voice_ai_enabled || false,
        website_url: tenant.website_url || "",
        textback_enabled: tenant.textback_enabled || false,
        textback_message:
          tenant.textback_message ||
          "Hi! Sorry we missed your call at {business_name}. How can we help? Reply here and we'll get back to you right away.",
        textback_quiet_start: tenant.textback_quiet_start || "22:00",
        textback_quiet_end: tenant.textback_quiet_end || "08:00",
      });
      setEmail(tenant.owner_email || "");
      setBusinessSlug(tenant.business_slug || null);
      setBusinessPageEnabled(!!tenant.business_page_enabled);
      setClientLoginEnabled(!!tenant.client_login_enabled);
      if (tenant.plan) setLivePlan(tenant.plan);
      const maybeProvisioned = tenant.notification_phone || "";
      setProvisionedPhone(
        maybeProvisioned.startsWith("+") ? maybeProvisioned : null,
      );
    } catch (err) {
      console.error("Failed to load settings", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (user?.tenantId && token) {
      fetchAiFeedback(user.tenantId, token)
        .then((data) => setFeedback(data.feedback || []))
        .catch((err) => console.warn("AI feedback fetch failed:", err.message));
      fetchKnowledgeStats(user.tenantId, token)
        .then((data) => setKnowledgeStats(data))
        .catch((err) =>
          console.warn("Knowledge stats fetch failed:", err.message),
        );
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    if (user?.tenantId && token) {
      getCrawlStatus(user.tenantId, token)
        .then((data) => setCrawlStatus(data))
        .catch((err) =>
          console.warn("Crawl status fetch failed:", err.message),
        );
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    if (user?.tenantId && token) {
      fetchTagDefinitions(user.tenantId, token)
        .then((data) => setTagDefs(data.tags || []))
        .catch((err) =>
          console.warn("Tag definitions fetch failed:", err.message),
        );
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    if (user?.tenantId && token) {
      setCfLoadError(null);
      fetchFieldDefinitions(user.tenantId, token)
        .then((data) =>
          setCustomFieldDefs(Array.isArray(data) ? data : data.fields || []),
        )
        .catch((err) => {
          console.warn("Custom field definitions fetch failed:", err.message);
          setCfLoadError("Could not load custom fields.");
        });
    }
  }, [user?.tenantId, token]);

  const handleAddCustomField = async () => {
    if (!newFieldName.trim()) return;
    setSavingField(true);
    try {
      const options =
        newFieldType === "dropdown"
          ? newFieldOptions
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : [];
      const created = await createFieldDefinition(user.tenantId, token, {
        name: newFieldName.trim(),
        field_type: newFieldType,
        options,
        is_required: newFieldRequired,
      });
      setCustomFieldDefs((prev) => [...prev, created]);
      setNewFieldName("");
      setNewFieldType("text");
      setNewFieldOptions("");
      setNewFieldRequired(false);
    } catch (err) {
      console.warn("Create custom field failed:", err.message);
      notify.error(err.message || "Failed to create field");
    } finally {
      setSavingField(false);
    }
  };

  const handleDeleteCustomField = async (fieldId) => {
    setDeletingFieldId(fieldId);
    try {
      await deleteFieldDefinition(user.tenantId, token, fieldId);
      setCustomFieldDefs((prev) => prev.filter((f) => f.id !== fieldId));
    } catch (err) {
      console.warn("Delete custom field failed:", err.message);
      notify.error(err.message || "Failed to delete field");
    } finally {
      setDeletingFieldId(null);
    }
  };

  const handleScanWebsite = async () => {
    if (!user?.tenantId) return;
    if (!form.website_url && !(businessSlug && businessPageEnabled)) return;
    setCrawling(true);
    try {
      if (form.website_url) {
        await updateTenantSettings(user.tenantId, token, {
          website_url: form.website_url,
        });
      }
      const result = await startWebsiteCrawl(user.tenantId, token);
      setCrawlStatus(result);
    } catch (err) {
      setCrawlStatus({ crawl_status: "failed", error_message: err.message });
    } finally {
      setCrawling(false);
    }
  };

  const handleDeleteFeedback = async (id) => {
    try {
      await deleteAiFeedback(user.tenantId, token, id);
      setFeedback((prev) => prev.filter((f) => f.id !== id));
    } catch (err) {
      console.warn("Delete feedback failed:", err.message);
    }
  };

  const handleAddTag = async () => {
    if (!newTagName.trim()) return;
    setSavingTag(true);
    try {
      const tag = await createTagDefinition(user.tenantId, token, {
        tag_name: newTagName.trim(),
        tag_color: newTagColor,
      });
      setTagDefs((prev) => [...prev, tag]);
      setNewTagName("");
      setNewTagColor("#6b7280");
    } catch (err) {
      console.warn("Create tag failed:", err.message);
    } finally {
      setSavingTag(false);
    }
  };

  const handleToggleTag = async (tag) => {
    try {
      await updateTagDefinition(user.tenantId, token, tag.id, {
        is_enabled: !tag.is_enabled,
      });
      setTagDefs((prev) =>
        prev.map((t) =>
          t.id === tag.id ? { ...t, is_enabled: !t.is_enabled } : t,
        ),
      );
    } catch (err) {
      console.warn("Toggle tag failed:", err.message);
    }
  };

  const handleDeleteTag = async (tagId) => {
    try {
      await deleteTagDefinition(user.tenantId, token, tagId);
      setTagDefs((prev) => prev.filter((t) => t.id !== tagId));
    } catch (err) {
      console.warn("Delete tag failed:", err.message);
    }
  };

  const handleSearchNumbers = async () => {
    if (!phoneAreaCode.trim()) return;
    setPhoneError(null);
    setPhoneSuccess(null);
    setAvailableNumbers([]);
    setSearchingNumbers(true);
    try {
      const res = await searchAvailableNumbers(
        user.tenantId,
        token,
        phoneAreaCode.trim(),
      );
      setAvailableNumbers(res.numbers || []);
      if (!res.numbers || res.numbers.length === 0) {
        setPhoneError(
          "No available numbers found for that area code. Try a different code.",
        );
      }
    } catch (err) {
      setPhoneError(err.message || "Failed to search for numbers.");
    } finally {
      setSearchingNumbers(false);
    }
  };

  const handleProvision = async () => {
    if (!phoneAreaCode.trim()) return;
    setPhoneError(null);
    setPhoneSuccess(null);
    setProvisioningPhone(true);
    try {
      const res = await provisionPhoneNumber(
        user.tenantId,
        token,
        phoneAreaCode.trim(),
      );
      setProvisionedPhone(res.phone_number);
      setAvailableNumbers([]);
      setPhoneAreaCode("");
      setPhoneSuccess(`Number ${res.phone_number} provisioned successfully.`);
      setForm((f) => ({ ...f, notification_phone: res.phone_number }));
    } catch (err) {
      setPhoneError(
        err.message || "Failed to provision number. Please try again.",
      );
    } finally {
      setProvisioningPhone(false);
    }
  };

  const handleReleasePhone = async () => {
    if (
      !window.confirm(
        "Are you sure you want to release this phone number? This cannot be undone.",
      )
    ) {
      return;
    }
    setPhoneError(null);
    setPhoneSuccess(null);
    setReleasingPhone(true);
    try {
      await releasePhoneNumber(user.tenantId, token);
      setProvisionedPhone(null);
      setAvailableNumbers([]);
      setPhoneSuccess("Phone number released.");
      setForm((f) => ({ ...f, notification_phone: "" }));
    } catch (err) {
      setPhoneError(
        err.message || "Failed to release number. Please try again.",
      );
    } finally {
      setReleasingPhone(false);
    }
  };

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setSaved(false);
  };

  const handleToggleClientLogin = async () => {
    if (!user?.tenantId || togglingClientLogin) return;
    setTogglingClientLogin(true);
    try {
      const data = await toggleClientLogin(user.tenantId, token);
      setClientLoginEnabled(data.client_login_enabled);
    } catch (err) {
      console.error("Failed to toggle client login", err);
    } finally {
      setTogglingClientLogin(false);
    }
  };

  const handleSave = async () => {
    if (!user?.tenantId) return;
    setSaving(true);
    try {
      await updateTenantSettings(user.tenantId, token, form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save settings", err);
      setSaveError(
        err?.body?.detail || err?.message || "Failed to save settings",
      );
      setTimeout(() => setSaveError(null), 5000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Settings</h1>
        <p>Manage your account and business information</p>
      </div>

      <SettingsPageContent
        apiBase={apiBase}
        onNavigate={onNavigate}
        logout={logout}
        form={form}
        setForm={setForm}
        saving={saving}
        saved={saved}
        setSaved={setSaved}
        saveError={saveError}
        handleChange={handleChange}
        handleSave={handleSave}
        email={email}
        livePlan={livePlan}
        feedback={feedback}
        knowledgeStats={knowledgeStats}
        crawlStatus={crawlStatus}
        crawling={crawling}
        handleScanWebsite={handleScanWebsite}
        businessSlug={businessSlug}
        businessPageEnabled={businessPageEnabled}
        clientLoginEnabled={clientLoginEnabled}
        togglingClientLogin={togglingClientLogin}
        handleToggleClientLogin={handleToggleClientLogin}
        tagDefs={tagDefs}
        newTagName={newTagName}
        setNewTagName={setNewTagName}
        newTagColor={newTagColor}
        setNewTagColor={setNewTagColor}
        savingTag={savingTag}
        handleAddTag={handleAddTag}
        handleToggleTag={handleToggleTag}
        handleDeleteTag={handleDeleteTag}
        customFieldDefs={customFieldDefs}
        cfLoadError={cfLoadError}
        newFieldName={newFieldName}
        setNewFieldName={setNewFieldName}
        newFieldType={newFieldType}
        setNewFieldType={setNewFieldType}
        newFieldOptions={newFieldOptions}
        setNewFieldOptions={setNewFieldOptions}
        newFieldRequired={newFieldRequired}
        setNewFieldRequired={setNewFieldRequired}
        savingField={savingField}
        deletingFieldId={deletingFieldId}
        handleAddCustomField={handleAddCustomField}
        handleDeleteCustomField={handleDeleteCustomField}
        provisionedPhone={provisionedPhone}
        phoneAreaCode={phoneAreaCode}
        setPhoneAreaCode={setPhoneAreaCode}
        availableNumbers={availableNumbers}
        setAvailableNumbers={setAvailableNumbers}
        searchingNumbers={searchingNumbers}
        provisioningPhone={provisioningPhone}
        releasingPhone={releasingPhone}
        phoneError={phoneError}
        phoneSuccess={phoneSuccess}
        setPhoneError={setPhoneError}
        handleSearchNumbers={handleSearchNumbers}
        handleProvision={handleProvision}
        handleReleasePhone={handleReleasePhone}
        handleDeleteFeedback={handleDeleteFeedback}
      />
    </div>
  );
}
