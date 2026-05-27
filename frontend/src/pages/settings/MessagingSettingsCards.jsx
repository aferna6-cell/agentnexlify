import { CheckboxSettingRow, SaveButton } from "./shared";

export function SmsNotificationsCard({
  form,
  setForm,
  setSaved,
  handleChange,
  handleSave,
  saving,
  saved,
}) {
  return (
    <div className="settings-card">
      <h3>SMS Notifications</h3>
      <p className="settings-card-desc">Get texted when new leads come in.</p>
      <div className="settings-field">
        <label>Phone Number</label>
        <input
          value={form.notification_phone}
          onChange={handleChange("notification_phone")}
          placeholder="+1 (555) 123-4567"
        />
      </div>
      <CheckboxSettingRow
        id="sms-toggle"
        checked={form.sms_notifications_enabled}
        onChange={(e) => {
          setForm((f) => ({
            ...f,
            sms_notifications_enabled: e.target.checked,
          }));
          setSaved(false);
        }}
        label="Enable SMS notifications for new leads"
      />
      <SaveButton
        saving={saving}
        saved={saved}
        onSave={handleSave}
        style={{ marginTop: "0.75rem" }}
      />
    </div>
  );
}

export function GoogleReviewLinkCard({
  form,
  handleChange,
  handleSave,
  saving,
  saved,
}) {
  return (
    <div className="settings-card">
      <h3>Google Review Link</h3>
      <p className="settings-card-desc">
        Paste your Google review URL here. Used by the Review Request automation
        template.
      </p>
      <div className="settings-field">
        <label>Review URL</label>
        <input
          value={form.google_review_link}
          onChange={handleChange("google_review_link")}
          placeholder="https://g.page/r/your-business/review"
        />
        <span className="settings-field-hint">
          Find this in Google Business Profile under "Ask for reviews"
        </span>
      </div>
      <SaveButton
        saving={saving}
        saved={saved}
        onSave={handleSave}
        style={{ marginTop: "0.75rem" }}
      />
    </div>
  );
}

export function AutoReviewRequestsCard({
  form,
  setForm,
  setSaved,
  handleSave,
  saving,
  saved,
}) {
  const updateReviewConfig = (patch) => {
    setForm((f) => ({
      ...f,
      review_request_config: { ...f.review_request_config, ...patch },
    }));
    setSaved(false);
  };

  return (
    <div className="settings-card">
      <h3>Auto Review Requests</h3>
      <p className="settings-card-desc">
        Automatically ask customers for a review after their appointment is
        completed.
        {!form.google_review_link && (
          <span
            style={{
              color: "var(--yellow, #facc15)",
              display: "block",
              marginTop: 4,
            }}
          >
            Set your Google Review Link above first.
          </span>
        )}
      </p>
      <CheckboxSettingRow
        id="review-req-toggle"
        checked={form.review_request_config.enabled}
        disabled={!form.google_review_link}
        onChange={(e) => updateReviewConfig({ enabled: e.target.checked })}
        label="Enable automatic review requests"
      />
      {form.review_request_config.enabled && (
        <>
          <div className="settings-field">
            <label>Send After</label>
            <select
              value={form.review_request_config.delay_hours}
              onChange={(e) =>
                updateReviewConfig({ delay_hours: parseInt(e.target.value) })
              }
              style={selectStyle}
            >
              <option value={0}>Immediately</option>
              <option value={1}>1 hour</option>
              <option value={24}>24 hours</option>
              <option value={48}>48 hours</option>
            </select>
          </div>
          <div className="settings-field">
            <label>Send Via</label>
            <select
              value={form.review_request_config.method}
              onChange={(e) => updateReviewConfig({ method: e.target.value })}
              style={selectStyle}
            >
              <option value="email">Email</option>
              <option value="sms">SMS</option>
              <option value="both">Email + SMS</option>
            </select>
          </div>
        </>
      )}
      <SaveButton
        saving={saving}
        saved={saved}
        onSave={handleSave}
        style={{ marginTop: "0.75rem" }}
      />
    </div>
  );
}

export function DailyBriefingCard({
  form,
  setForm,
  setSaved,
  handleSave,
  saving,
  saved,
}) {
  return (
    <div className="settings-card">
      <h3>Daily Briefing SMS</h3>
      <p className="settings-card-desc">
        Get a morning text message with your new leads, today&apos;s
        appointments, pending tasks, and unread conversations.
        {!form.notification_phone && (
          <span
            style={{
              color: "var(--yellow, #facc15)",
              display: "block",
              marginTop: 4,
            }}
          >
            Set a phone number above first.
          </span>
        )}
      </p>
      <CheckboxSettingRow
        id="briefing-toggle"
        checked={form.daily_briefing_enabled}
        disabled={!form.notification_phone || !form.sms_notifications_enabled}
        onChange={(e) => {
          setForm((f) => ({
            ...f,
            daily_briefing_enabled: e.target.checked,
          }));
          setSaved(false);
        }}
        label="Enable daily morning briefing"
      />
      <SaveButton
        saving={saving}
        saved={saved}
        onSave={handleSave}
        style={{ marginTop: "0.75rem" }}
      />
    </div>
  );
}

export function NoShowRecoveryCard({
  form,
  setForm,
  setSaved,
  handleSave,
  saving,
  saved,
}) {
  return (
    <div className="settings-card">
      <h3>No-Show Recovery</h3>
      <p className="settings-card-desc">
        Automatically send a friendly SMS and email to customers who miss their
        appointment, with an easy link to reschedule.
      </p>
      <CheckboxSettingRow
        id="noshow-toggle"
        checked={form.noshow_recovery_enabled}
        onChange={(e) => {
          setForm((f) => ({
            ...f,
            noshow_recovery_enabled: e.target.checked,
          }));
          setSaved(false);
        }}
        label="Enable no-show recovery outreach"
      />
      <SaveButton
        saving={saving}
        saved={saved}
        onSave={handleSave}
        style={{ marginTop: "0.75rem" }}
      />
    </div>
  );
}

export function AgentOSAutoSendCard({
  form,
  setForm,
  setSaved,
  handleSave,
  saving,
  saved,
}) {
  return (
    <div className="settings-card">
      <h3>Agent OS Auto-Send</h3>
      <p className="settings-card-desc">
        When OFF (default), every Agent OS worker deliverable waits for your
        approval before any customer-facing action fires. When ON, deliverables
        are auto-approved as soon as the worker completes — no review gate. Only
        turn ON once you trust the workers and prompts.
      </p>
      <CheckboxSettingRow
        id="os-auto-send-toggle"
        checked={form.os_auto_send_enabled}
        onChange={(e) => {
          setForm((f) => ({
            ...f,
            os_auto_send_enabled: e.target.checked,
          }));
          setSaved(false);
        }}
        label="Skip approval — auto-send worker deliverables"
      />
      <SaveButton
        saving={saving}
        saved={saved}
        onSave={handleSave}
        style={{ marginTop: "0.75rem" }}
      />
    </div>
  );
}

export function MissedCallTextBackCard({
  form,
  setForm,
  setSaved,
  handleSave,
  saving,
  saved,
}) {
  const updateTextBack = (patch) => {
    setForm((f) => ({ ...f, ...patch }));
    setSaved(false);
  };

  return (
    <div className="settings-card">
      <h3>Missed Call Text-Back</h3>
      <p className="settings-card-desc">
        Automatically send a text message when you miss a phone call, so
        potential customers get an instant response.
      </p>
      <CheckboxSettingRow
        id="textback-toggle"
        checked={form.textback_enabled}
        onChange={(e) => updateTextBack({ textback_enabled: e.target.checked })}
        label="Enable missed call text-back"
      />
      {form.textback_enabled && (
        <>
          <div className="settings-field">
            <label>Greeting Message</label>
            <textarea
              value={form.textback_message}
              onChange={(e) =>
                updateTextBack({ textback_message: e.target.value })
              }
              rows={3}
              style={textareaStyle}
              placeholder="Hi! Sorry we missed your call..."
            />
            <span className="settings-field-hint">
              Use {"{business_name}"} to insert your business name automatically
            </span>
          </div>
          <div className="settings-field">
            <label>Quiet Hours</label>
            <p
              style={{
                fontSize: "0.8rem",
                color: "var(--text-muted)",
                margin: "0 0 8px",
              }}
            >
              Don't send text-backs during these hours (e.g., late night).
              Missed calls during quiet hours will be texted when quiet hours
              end.
            </p>
            <div
              style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}
            >
              <QuietHourInput
                label="Start"
                value={form.textback_quiet_start}
                onChange={(value) =>
                  updateTextBack({ textback_quiet_start: value })
                }
              />
              <span style={{ color: "var(--text-muted)", marginTop: 18 }}>
                to
              </span>
              <QuietHourInput
                label="End"
                value={form.textback_quiet_end}
                onChange={(value) =>
                  updateTextBack({ textback_quiet_end: value })
                }
              />
            </div>
          </div>
        </>
      )}
      <SaveButton
        saving={saving}
        saved={saved}
        onSave={handleSave}
        style={{ marginTop: "0.75rem" }}
      />
    </div>
  );
}

function QuietHourInput({ label, value, onChange }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
        {label}
      </span>
      <input
        type="time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          padding: "6px 10px",
          borderRadius: 6,
          border: "1px solid var(--border)",
          background: "var(--bg-secondary)",
          color: "var(--text-primary)",
          fontSize: "0.9rem",
        }}
      />
    </div>
  );
}

const selectStyle = {
  padding: "6px 10px",
  borderRadius: 6,
  border: "1px solid var(--border)",
  background: "var(--bg-secondary)",
  color: "var(--text-primary)",
};

const textareaStyle = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 6,
  border: "1px solid var(--border)",
  background: "var(--bg-secondary)",
  color: "var(--text-primary)",
  resize: "vertical",
  fontFamily: "inherit",
  fontSize: "0.9rem",
};
