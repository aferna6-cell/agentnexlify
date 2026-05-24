export default function TestStep({
  showPreview,
  onTestPreview,
  apiKey,
  apiBase,
}) {
  return (
    <div className="onboarding-step-body">
      <p className="onboarding-hint">
        Click below to preview your widget and try chatting with your AI
        assistant.
      </p>
      {!showPreview ? (
        <button className="onboarding-save-btn" onClick={onTestPreview}>
          Preview Widget
        </button>
      ) : (
        <div className="onboarding-preview-container">
          <iframe
            title="Widget Preview"
            className="onboarding-preview-iframe"
            src={`https://app.agentnexlify.com/widget/preview.html?key=${encodeURIComponent(apiKey || "")}&base=${encodeURIComponent(apiBase)}`}
          />
        </div>
      )}
    </div>
  );
}
