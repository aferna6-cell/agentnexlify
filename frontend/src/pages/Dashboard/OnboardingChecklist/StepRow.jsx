export default function StepRow({
  step,
  index,
  isActive,
  isClickable,
  onToggle,
  children,
}) {
  return (
    <div
      className={`onboarding-step${step.complete ? " complete" : ""}${isActive ? " active" : ""}`}
    >
      <div
        className="onboarding-step-header"
        onClick={() => isClickable && onToggle()}
        style={{ cursor: isClickable ? "pointer" : "default" }}
      >
        <div className="onboarding-step-icon">
          {step.complete ? (
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
          ) : (
            <span className="onboarding-step-number">{index + 1}</span>
          )}
        </div>
        <div className="onboarding-step-info">
          <div className="onboarding-step-title">{step.title}</div>
          <div className="onboarding-step-desc">{step.description}</div>
        </div>
        <span className="onboarding-step-chevron">{isActive ? "▲" : "▼"}</span>
      </div>
      {isActive && <div className="onboarding-step-content">{children}</div>}
    </div>
  );
}
