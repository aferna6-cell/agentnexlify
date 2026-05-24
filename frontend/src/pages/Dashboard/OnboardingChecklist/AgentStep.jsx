export default function AgentStep({
  greeting,
  setGreeting,
  saving,
  saveError,
  onSaveGreeting,
  services,
  newService,
  setNewService,
  addingService,
  onAddService,
  faqEntries,
  newFaqQ,
  setNewFaqQ,
  newFaqA,
  setNewFaqA,
  onAddFaq,
  onDeleteFaq,
  faqError,
}) {
  return (
    <div className="onboarding-step-body">
      <label className="onboarding-field-label">Greeting Message</label>
      <textarea
        className="onboarding-textarea"
        value={greeting}
        onChange={(e) => setGreeting(e.target.value)}
        rows={3}
        placeholder="Hi! How can I help you today?"
      />
      <button
        className="onboarding-save-btn"
        onClick={onSaveGreeting}
        disabled={saving}
      >
        {saving ? "Saving..." : "Save Greeting"}
      </button>
      {saveError && <div className="onboarding-error">{saveError}</div>}

      <div className="onboarding-faq-section" style={{ marginTop: 12 }}>
        <label className="onboarding-field-label">Your Services</label>
        <p
          className="onboarding-hint"
          style={{ marginBottom: 6, fontSize: "0.82rem" }}
        >
          Add your services so the AI can answer questions about what you offer.
        </p>
        {services.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
              marginBottom: 8,
            }}
          >
            {services.map((s, i) => (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  padding: "4px 10px",
                  borderRadius: 14,
                  fontSize: "0.78rem",
                  background: "var(--accent-dim, rgba(0,191,255,0.15))",
                  color: "var(--accent, #00BFFF)",
                  border: "1px solid var(--accent-dim, rgba(0,191,255,0.25))",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        )}
        <div style={{ display: "flex", gap: 6 }}>
          <input
            className="onboarding-input"
            placeholder="e.g. Plumbing Repair, Drain Cleaning"
            value={newService}
            onChange={(e) => setNewService(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onAddService()}
            style={{ flex: 1 }}
          />
          <button
            className="onboarding-add-btn"
            onClick={onAddService}
            disabled={addingService || !newService.trim()}
          >
            {addingService ? "Adding..." : "Add"}
          </button>
        </div>
      </div>

      <div className="onboarding-faq-section">
        <label className="onboarding-field-label">
          FAQ Entries ({faqEntries.length})
        </label>
        {faqEntries.map((faq) => (
          <div className="onboarding-faq-item" key={faq.id}>
            <div className="onboarding-faq-q">Q: {faq.question}</div>
            <div className="onboarding-faq-a">A: {faq.answer}</div>
            <button
              className="onboarding-faq-delete"
              onClick={() => onDeleteFaq(faq.id)}
            >
              Remove
            </button>
          </div>
        ))}
        <div className="onboarding-faq-form">
          <input
            className="onboarding-input"
            placeholder="Question"
            value={newFaqQ}
            onChange={(e) => setNewFaqQ(e.target.value)}
          />
          <input
            className="onboarding-input"
            placeholder="Answer"
            value={newFaqA}
            onChange={(e) => setNewFaqA(e.target.value)}
          />
          <button
            className="onboarding-add-btn"
            onClick={onAddFaq}
            disabled={saving || !newFaqQ.trim() || !newFaqA.trim()}
          >
            {saving ? "Adding..." : "Add FAQ"}
          </button>
          {faqError && <div className="onboarding-error">{faqError}</div>}
        </div>
      </div>
    </div>
  );
}
