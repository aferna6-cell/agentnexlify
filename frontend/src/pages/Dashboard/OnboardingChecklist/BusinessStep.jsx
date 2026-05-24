export default function BusinessStep({ dashData }) {
  const plan = dashData?.plan || "free";
  const planLabel = plan.charAt(0).toUpperCase() + plan.slice(1);

  return (
    <div className="onboarding-step-body">
      <div className="onboarding-info-row">
        <span className="onboarding-info-label">Business Name</span>
        <span className="onboarding-info-value">
          {dashData?.business_name || "Not set"}
        </span>
      </div>
      <div className="onboarding-info-row">
        <span className="onboarding-info-label">Plan</span>
        <span className="onboarding-info-value">{planLabel}</span>
      </div>
      <p className="onboarding-hint">
        Business info was set during signup. You can update it from Settings.
      </p>
    </div>
  );
}
