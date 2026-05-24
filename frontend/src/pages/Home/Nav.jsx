import { Link } from "react-router-dom";

export default function Nav({
  navScrolled,
  menuOpen,
  isLoggedIn,
  toggleMenu,
  closeMenu,
}) {
  return (
    <nav
      className={`lp-nav${navScrolled ? " scrolled" : ""}`}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="lp-nav-inner">
        <a href="/" className="lp-nav-logo">
          <img src="/logo.png" alt="Agent NexLiFy" />
          <span>NexLiFy</span>
        </a>

        <div className={`lp-nav-links${menuOpen ? " open" : ""}`}>
          <a href="#how-it-works" onClick={closeMenu}>
            How It Works
          </a>
          <a href="#features" onClick={closeMenu}>
            Features
          </a>
          <a href="#pricing" onClick={closeMenu}>
            Pricing
          </a>
          <a href="#demo" onClick={closeMenu}>
            Demo
          </a>
          <a href="#faq" onClick={closeMenu}>
            FAQ
          </a>
        </div>

        <div className="lp-nav-actions">
          {isLoggedIn ? (
            <Link to="/dashboard" className="lp-nav-cta">
              Dashboard
            </Link>
          ) : (
            <>
              <Link to="/login" className="lp-nav-login">
                <span>Log In</span>
              </Link>
              <Link to="/signup" className="lp-nav-cta">
                Get Started
              </Link>
            </>
          )}
        </div>

        <button
          className={`lp-nav-toggle${menuOpen ? " active" : ""}`}
          aria-label="Toggle menu"
          aria-expanded={menuOpen ? "true" : "false"}
          onClick={toggleMenu}
        >
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
    </nav>
  );
}
