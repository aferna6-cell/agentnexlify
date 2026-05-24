import { Link } from "react-router-dom";

export default function FinalCta() {
  return (
    <section className="lp-cta-section" id="cta">
      <div className="container lp-cta-content">
        <h2 className="section-title reveal">Ready to book more jobs?</h2>
        <div className="lp-cta-buttons reveal">
          <Link to="/signup" className="btn-primary">
            Get Started {"→"}
          </Link>
          <Link to="/demo" className="btn-secondary">
            Book a Demo
          </Link>
        </div>
      </div>
    </section>
  );
}
