import { Link } from "react-router-dom";

export default function Hero() {
  return (
    <section className="lp-hero">
      <div className="container">
        <div className="lp-hero-inner">
          <div className="lp-hero-text">
            <h1 className="reveal">
              Your hardest working employee that dosen&apos;t stop. It answers,
              follows up, and continues to push the buisness forward{" "}
              <span className="accent-gradient">around the clock.</span>
            </h1>
            <p
              className="reveal"
              style={{
                marginTop: "1rem",
                marginBottom: "1.5rem",
                color: "var(--text-secondary)",
                maxWidth: 560,
              }}
            >
              Your 24/7 AI front desk that talks to customers, captures leads,
              books appointments, and follows up automatically. Install in 30
              seconds. Start free, then from $99/mo.
            </p>
            <div className="lp-hero-buttons reveal">
              <Link to="/signup" className="btn-primary">
                Embed widget free {"→"}
              </Link>
              <a href="#how-it-works" className="btn-secondary">
                See how it works
              </a>
            </div>
          </div>

          <div className="widget-mockup reveal">
            <div className="widget-mockup-header">
              <div className="widget-mockup-avatar">AI</div>
              <div className="widget-mockup-header-text">
                <div className="widget-mockup-name">Your Business</div>
                <div className="widget-mockup-status">
                  <span className="widget-mockup-status-dot"></span>
                  Online
                </div>
              </div>
            </div>
            <div className="widget-mockup-body">
              <div className="wm-msg wm-msg-bot">
                Hi! How can I help you today?
              </div>
              <div className="wm-msg wm-msg-user">
                Hi, I&apos;d like to book a reservation for this Saturday
              </div>
              <div className="wm-typing" aria-hidden="true">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div className="wm-msg wm-msg-bot">
                I&apos;d love to help! Could I get your name?
              </div>
              <div className="wm-msg wm-msg-user">Sarah Johnson</div>
              <div className="wm-msg wm-msg-bot">
                Thanks Sarah! Let me check availability for Saturday...
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
