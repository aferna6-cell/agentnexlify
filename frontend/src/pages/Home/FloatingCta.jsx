import { Link } from "react-router-dom";

export default function FloatingCta({ visible, onDismiss }) {
  if (!visible) return null;
  return (
    <div className="lp-floating-cta">
      <Link to="/signup" className="lp-floating-cta-link">
        <span className="floating-cta-full">Try our AI assistant free</span>
        <span className="floating-cta-short">Try Out Our AI Assistant</span>
      </Link>
      <button
        className="lp-floating-cta-close"
        onClick={onDismiss}
        aria-label="Dismiss"
      >
        {"×"}
      </button>
    </div>
  );
}
