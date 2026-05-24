export default function AutomationsStep({
  existingSequences,
  sequenceCreated,
  creatingSequence,
  sequenceError,
  textbackEnabled,
  savingTextback,
  onCreateDefaultSequence,
  onToggleTextback,
  onSkipAutomations,
  onNavigate,
}) {
  const hasSequences =
    sequenceCreated || (existingSequences && existingSequences.length > 0);

  return (
    <div className="onboarding-step-body">
      <p className="onboarding-hint">
        Automations let your AI follow up with new leads automatically. Create a
        welcome email sequence so every lead hears from you within minutes - no
        manual work needed.
      </p>
      {existingSequences === null ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            color: "var(--text-muted)",
            fontSize: "0.85rem",
          }}
        >
          <span className="onboarding-spinner" /> Loading sequences...
        </div>
      ) : hasSequences ? (
        <div className="onboarding-automation-done">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 10,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="10" fill="var(--green)" />
              <path
                d="M6 10l3 3 5-6"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span
              style={{
                fontSize: "0.9rem",
                fontWeight: 600,
                color: "var(--green)",
              }}
            >
              {existingSequences && existingSequences.length > 0
                ? `${existingSequences.length} automation sequence${existingSequences.length > 1 ? "s" : ""} active`
                : "Welcome sequence created"}
            </span>
          </div>
          <button
            className="onboarding-add-btn"
            onClick={() => onNavigate?.("automations")}
          >
            View Automations
          </button>
        </div>
      ) : (
        <>
          <div className="onboarding-automation-preview">
            <div
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--text-primary)",
                marginBottom: 8,
              }}
            >
              Welcome Email Sequence
            </div>
            <div className="automation-preview-steps">
              <div className="automation-preview-step">
                <span className="automation-step-badge">1</span>
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-secondary)",
                  }}
                >
                  Instant welcome email when a new lead arrives
                </span>
              </div>
              <div className="automation-preview-connector" />
              <div className="automation-preview-step">
                <span className="automation-step-badge">2</span>
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-secondary)",
                  }}
                >
                  Follow-up email after 24 hours if no reply
                </span>
              </div>
              <div className="automation-preview-connector" />
              <div className="automation-preview-step">
                <span className="automation-step-badge">3</span>
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-secondary)",
                  }}
                >
                  Final check-in after 3 days
                </span>
              </div>
            </div>
          </div>
          <button
            className="onboarding-save-btn"
            onClick={onCreateDefaultSequence}
            disabled={creatingSequence}
          >
            {creatingSequence ? "Creating..." : "Create Default Sequences"}
          </button>
          {sequenceError && (
            <div className="onboarding-error">{sequenceError}</div>
          )}
          <button
            className="onboarding-add-btn"
            onClick={onSkipAutomations}
            style={{ marginTop: 4 }}
          >
            Skip - I'll set up my own
          </button>
        </>
      )}

      <div
        style={{
          marginTop: 16,
          paddingTop: 12,
          borderTop: "1px solid var(--border, #2a2a3e)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--text-primary)",
              }}
            >
              Missed Call Text-Back
            </div>
            <div
              style={{
                fontSize: "0.78rem",
                color: "var(--text-muted)",
                marginTop: 2,
              }}
            >
              Auto-text callers when you miss their call
            </div>
          </div>
          <button
            className="btn-sm"
            onClick={() => onToggleTextback(!textbackEnabled)}
            disabled={savingTextback}
            style={{
              background: textbackEnabled
                ? "var(--green, #22c55e)"
                : "var(--bg-darker, #1a1a2e)",
              minWidth: 60,
              fontSize: "0.78rem",
            }}
          >
            {savingTextback ? "..." : textbackEnabled ? "On" : "Off"}
          </button>
        </div>
      </div>
    </div>
  );
}
