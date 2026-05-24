export default function LiveStep({ onNavigate, onFinish }) {
  return (
    <div className="onboarding-step-body onboarding-live">
      <div className="onboarding-celebration">
        <span className="celebration-emoji">
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        </span>
        <h3>Congratulations!</h3>
        <p>Your AI assistant is live and ready to capture leads.</p>
      </div>
      <div className="onboarding-next-steps">
        <button
          className="onboarding-next-btn"
          onClick={() => onNavigate?.("automations")}
        >
          Set up Automations
        </button>
        <button
          className="onboarding-next-btn"
          onClick={() => onNavigate?.("leads")}
        >
          View Leads
        </button>
        <button
          className="onboarding-next-btn"
          onClick={() => onNavigate?.("billing")}
        >
          Manage Billing
        </button>
      </div>
      <button className="onboarding-finish-btn" onClick={onFinish}>
        Close Setup
      </button>
    </div>
  );
}
