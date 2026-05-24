import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="lp-footer">
      <div className="container">
        <div className="lp-footer-inner">
          <div className="lp-footer-brand">
            <img
              src="/logo.png"
              alt="Agent NexLiFy Logo"
              className="lp-footer-brand-logo"
            />
            <p>A friendly AI assistant for your business.</p>
          </div>
          <div className="lp-footer-col">
            <h4>Product</h4>
            <ul>
              <li>
                <a href="#how-it-works">How It Works</a>
              </li>
              <li>
                <a href="#features">Features</a>
              </li>
              <li>
                <a href="#faq">FAQ</a>
              </li>
            </ul>
          </div>
          <div className="lp-footer-col">
            <h4>Company</h4>
            <ul>
              <li>
                <Link to="/contact">Contact</Link>
              </li>
              <li>
                <Link to="/demo">Book a Demo</Link>
              </li>
            </ul>
          </div>
          <div className="lp-footer-col">
            <h4>Legal</h4>
            <ul>
              <li>
                <Link to="/privacy">Privacy Policy</Link>
              </li>
              <li>
                <Link to="/terms">Terms of Service</Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="lp-footer-bottom">
          <span className="lp-footer-copy">
            &copy; 2026 Agent NexLiFy. All rights reserved.
          </span>
        </div>
      </div>
    </footer>
  );
}
