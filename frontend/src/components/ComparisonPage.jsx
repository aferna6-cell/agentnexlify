import React, { useState, useEffect, useCallback, useRef } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import "../styles/home.css";
import "../styles/comparison.css";

const CALENDLY_URL = "https://calendly.com/aidanfernandes31/15-minute-agent-nexliffy-demo";

/* ── SVG icons for reason cards ── */
const REASON_ICONS = {
  dollar: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  zap: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  phone: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  ),
  moon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  ),
  bot: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="10" rx="2" /><circle cx="12" cy="5" r="2" /><path d="M12 7v4" /><line x1="8" y1="16" x2="8" y2="16" /><line x1="16" y1="16" x2="16" y2="16" />
    </svg>
  ),
  target: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" />
    </svg>
  ),
  tag: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" /><line x1="7" y1="7" x2="7.01" y2="7" />
    </svg>
  ),
};

export default function ComparisonPage({ meta, hero, comparison, reasons, crossLinks, faq, cta }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [openFaq, setOpenFaq] = useState(null);
  const faqRefs = useRef({});
  const revealRefs = useRef([]);

  // Nav scroll
  useEffect(() => {
    function check() { setScrolled(window.scrollY > 20); }
    window.addEventListener("scroll", check, { passive: true });
    check();
    return () => window.removeEventListener("scroll", check);
  }, []);

  // Reveal animations
  useEffect(() => {
    const els = revealRefs.current.filter(Boolean);
    if (!("IntersectionObserver" in window)) { els.forEach((el) => el.classList.add("visible")); return; }
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("visible"); obs.unobserve(e.target); } }),
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  const toggleMenu = useCallback(() => {
    setMenuOpen((p) => { const n = !p; document.body.style.overflow = n ? "hidden" : ""; return n; });
  }, []);
  const closeMenu = useCallback(() => { setMenuOpen(false); document.body.style.overflow = ""; }, []);

  const handleFaqToggle = useCallback((id) => {
    setOpenFaq((prev) => (prev === id ? null : id));
  }, []);

  const getFaqMaxHeight = useCallback((id) => {
    if (openFaq === id && faqRefs.current[id]) return faqRefs.current[id].scrollHeight + "px";
    return "0";
  }, [openFaq]);

  const revealRef = (el) => { if (el && !revealRefs.current.includes(el)) revealRefs.current.push(el); };

  return (
    <>
      <Helmet>
        <title>{meta.title}</title>
        <meta name="description" content={meta.description} />
        <link rel="canonical" href={meta.canonical} />
        <meta property="og:title" content={meta.title} />
        <meta property="og:description" content={meta.description} />
        <meta property="og:url" content={meta.canonical} />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={meta.title} />
        <meta name="twitter:description" content={meta.description} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </Helmet>

      {/* ============ NAV ============ */}
      <nav className={`nav${scrolled ? " scrolled" : ""}`} role="navigation" aria-label="Main navigation">
        <div className="nav-inner">
          <button className={`nav-toggle${menuOpen ? " active" : ""}`} aria-label="Toggle menu" aria-expanded={menuOpen} onClick={toggleMenu}>
            <span></span><span></span><span></span>
          </button>
          <ul className={`nav-left${menuOpen ? " open" : ""}`}>
            <li><Link to="/" onClick={closeMenu}>Home</Link></li>
            <li><a href="/#pricing" onClick={closeMenu}>Pricing</a></li>
            <li><a href="/#features" onClick={closeMenu}>Features</a></li>
            <li><a href="/#faq" onClick={closeMenu}>FAQ</a></li>
          </ul>
          <Link to="/" className="nav-logo">
            <img src="/logo.png" alt="Agent NexLiFy" />
          </Link>
          <div className="nav-right">
            <a href={CALENDLY_URL} className="nav-login">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><polyline points="10 17 15 12 10 7" /><line x1="15" y1="12" x2="3" y2="12" />
              </svg>
              <span>Book Demo</span>
            </a>
            <Link to="/signup" className="nav-cta">Start Free</Link>
          </div>
        </div>
      </nav>

      {/* ============ HERO ============ */}
      <section className="hero">
        <div className="container hero-content">
          <h1 className="reveal" ref={revealRef}>
            {hero.h1}<br />
            <span className="accent">{hero.h1Accent}</span>
          </h1>
          <p className="hero-sub reveal" ref={revealRef}>{hero.subtitle}</p>
          <div className="hero-buttons reveal" ref={revealRef}>
            <a href={CALENDLY_URL} className="btn-primary">{hero.primaryCta}</a>
            <a href="#comparison" className="btn-secondary">{hero.secondaryCta}</a>
          </div>
        </div>
      </section>

      {/* ============ COMPARISON TABLE ============ */}
      <section className="section compare-section" id="comparison">
        <div className="container">
          <div className="compare-header">
            <div className="section-label reveal" ref={revealRef}>{comparison.label}</div>
            <h2 className="section-title reveal" ref={revealRef}>{comparison.title}</h2>
            <p className="section-subtitle reveal" ref={revealRef}>{comparison.subtitle}</p>
          </div>
          <div className="compare-table-wrap reveal" ref={revealRef}>
            <table className="compare-table">
              <thead>
                <tr>
                  {comparison.columns.map((col, i) => (
                    <th key={i} className={i === 1 ? "col-nexlify" : ""}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparison.rows.map((row, i) => (
                  <tr key={i}>
                    <td>{row.feature}</td>
                    <td className={`col-nexlify ${row.nexlifyClass}`}>{row.nexlify}</td>
                    <td className={row.competitorClass}>{row.competitor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ============ REASONS ============ */}
      <section className="section reasons">
        <div className="container">
          <div className="reasons-header">
            <div className="section-label reveal" ref={revealRef}>{reasons.label}</div>
            <h2 className="section-title reveal" ref={revealRef}>{reasons.title}</h2>
          </div>
          <div className="reasons-grid">
            {reasons.cards.map((card, i) => (
              <div key={i} className="reason-card reveal" ref={revealRef}>
                <div className="reason-icon" aria-hidden="true">
                  {REASON_ICONS[card.icon]}
                </div>
                <h3>{card.heading}</h3>
                <p>{card.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ CROSS LINKS ============ */}
      <div className="cross-links">
        <div className="container">
          <p>
            Also comparing:{" "}
            {crossLinks.others.map((link, i) => (
              <React.Fragment key={link.slug}>
                {i > 0 && <span className="sep">|</span>}
                <Link to={`/${link.slug}`}>{link.label}</Link>
              </React.Fragment>
            ))}
          </p>
        </div>
      </div>

      {/* ============ FAQ ============ */}
      <section className="section faq">
        <div className="container">
          <div className="faq-header">
            <div className="section-label reveal" ref={revealRef}>FAQ</div>
            <h2 className="section-title reveal" ref={revealRef}>Common Questions</h2>
          </div>
          <div className="faq-list">
            {faq.items.map((item, i) => (
              <div key={i} className="faq-item">
                <button
                  className="faq-question"
                  aria-expanded={openFaq === i}
                  aria-controls={`faq-${i}`}
                  onClick={() => handleFaqToggle(i)}
                >
                  <span>{item.question}</span>
                  <svg className="faq-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
                <div
                  className="faq-answer"
                  id={`faq-${i}`}
                  role="region"
                  ref={(el) => { faqRefs.current[i] = el; }}
                  style={{ maxHeight: getFaqMaxHeight(i) }}
                >
                  <div className="faq-answer-inner">{item.answer}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ CTA ============ */}
      <section className="cta-section">
        <div className="container cta-content">
          <h2 className="section-title reveal" ref={revealRef}>{cta.title}</h2>
          <p className="section-subtitle reveal" ref={revealRef}>{cta.subtitle}</p>
          <div className="hero-buttons reveal" ref={revealRef} style={{ marginBottom: 0 }}>
            <a href={CALENDLY_URL} className="btn-primary">{cta.primaryCta}</a>
            <a href="/#pricing" className="btn-secondary">{cta.secondaryCta}</a>
          </div>
          <p className="cta-note reveal" ref={revealRef}>{cta.note}</p>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <footer className="footer">
        <div className="container">
          <div className="footer-inner">
            <div className="footer-brand">
              <img src="/logo.png" alt="Agent NexLiFy Logo" className="footer-brand-logo" />
              <p>AI-powered operations for businesses.</p>
              <Link to="/signup" className="btn-primary" style={{ marginTop: "16px", fontSize: "14px", padding: "12px 24px" }}>
                Start Free {"\u2192"}
              </Link>
            </div>
            <div className="footer-col">
              <h4>Product</h4>
              <ul>
                <li><a href="/#features">Features</a></li>
                <li><a href="/#pricing">Pricing</a></li>
                <li><a href="/#faq">FAQ</a></li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>Compare</h4>
              <ul>
                <li><Link to="/intercom-alternative">vs. Intercom</Link></li>
                <li><Link to="/livechat-alternative">vs. LiveChat</Link></li>
                <li><Link to="/tidio-alternative">vs. Tidio</Link></li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>Company</h4>
              <ul>
                <li><a href="/#why">Why Us</a></li>
                <li><a href="mailto:hello@agentnexlify.com">Contact</a></li>
              </ul>
            </div>
          </div>
          <div className="footer-bottom">
            <span className="footer-copy">&copy; 2026 Agent NexLiFy. All rights reserved.</span>
            <div className="footer-socials">
              <a href="#" aria-label="Twitter / X">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>
              </a>
              <a href="#" aria-label="LinkedIn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" /></svg>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}

export { REASON_ICONS };
