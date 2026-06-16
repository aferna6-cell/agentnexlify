import { useState, useEffect, useCallback, useRef } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import "../styles/free-widget.css";

export default function FreeWidget() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const revealRefs = useRef([]);

  // Nav scroll detection
  useEffect(() => {
    function checkScroll() {
      setScrolled(window.scrollY > 20);
    }
    window.addEventListener("scroll", checkScroll, { passive: true });
    checkScroll();
    return () => window.removeEventListener("scroll", checkScroll);
  }, []);

  // Reveal animations with IntersectionObserver
  useEffect(() => {
    const elements = revealRefs.current.filter(Boolean);
    if (!("IntersectionObserver" in window)) {
      elements.forEach((el) => el.classList.add("visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    );
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Toggle mobile menu
  const toggleMenu = useCallback(() => {
    setMenuOpen((prev) => {
      const next = !prev;
      document.body.style.overflow = next ? "hidden" : "";
      return next;
    });
  }, []);

  // Close mobile menu on nav link click
  const closeMenu = useCallback(() => {
    setMenuOpen(false);
    document.body.style.overflow = "";
  }, []);

  // Helper to register reveal refs
  let revealIndex = 0;
  const revealRef = (el) => {
    if (el && !revealRefs.current.includes(el)) {
      revealRefs.current.push(el);
    }
  };

  const softwareAppLdJson = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "AgentNexLiFy",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    description:
      "AI-powered customer service chatbot for websites. Capture leads, answer questions, and book appointments 24/7.",
    url: "https://agentnexlify.com/free-widget",
    offers: [
      {
        "@type": "Offer",
        name: "Chatbot",
        price: "19.99",
        priceCurrency: "USD",
        priceSpecification: {
          "@type": "UnitPriceSpecification",
          price: "19.99",
          priceCurrency: "USD",
          billingDuration: "P1M",
        },
        description:
          "AI chatbot widget, lead capture, FAQ answers, appointment booking, email notifications",
      },
      {
        "@type": "Offer",
        name: "Agent OS",
        price: "99.99",
        priceCurrency: "USD",
        priceSpecification: {
          "@type": "UnitPriceSpecification",
          price: "99.99",
          priceCurrency: "USD",
          billingDuration: "P1M",
        },
        description:
          "Full platform: AI staff, Agent OS, marketing, SEO, social media, campaigns, and everything in Chatbot",
      },
    ],
  });

  const organizationLdJson = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "AgentNexLiFy",
    url: "https://agentnexlify.com",
    logo: "https://agentnexlify.com/logo.png",
    description: "AI-powered customer service platform for local businesses",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Clemson",
      addressRegion: "SC",
      addressCountry: "US",
    },
  });

  return (
    <>
      <Helmet>
        <title>AI Chatbot for Your Website | AgentNexLiFy</title>
        <meta
          name="description"
          content="Add an AI chatbot to your website in minutes. Handle customer inquiries 24/7, capture leads automatically, no coding required."
        />
        <link rel="canonical" href="https://agentnexlify.com/free-widget" />
        <meta
          property="og:title"
          content="AI Chatbot for Your Website | AgentNexLiFy"
        />
        <meta
          property="og:description"
          content="Add an AI chatbot to your website in minutes. Handle customer inquiries 24/7, capture leads automatically, no coding required."
        />
        <meta
          property="og:url"
          content="https://agentnexlify.com/free-widget"
        />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta
          name="twitter:title"
          content="AI Chatbot for Your Website | AgentNexLiFy"
        />
        <meta
          name="twitter:description"
          content="Add an AI chatbot to your website in minutes. Handle customer inquiries 24/7, capture leads automatically, no coding required."
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Outfit:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
        <script type="application/ld+json">{softwareAppLdJson}</script>
        <script type="application/ld+json">{organizationLdJson}</script>
      </Helmet>

      {/* ============ NAV ============ */}
      <nav
        className={`nav${scrolled ? " scrolled" : ""}`}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="nav-inner">
          <button
            className={`nav-toggle${menuOpen ? " active" : ""}`}
            aria-label="Toggle menu"
            aria-expanded={menuOpen ? "true" : "false"}
            onClick={toggleMenu}
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
          <ul className={`nav-left${menuOpen ? " open" : ""}`}>
            <li>
              <Link to="/" onClick={closeMenu}>
                Home
              </Link>
            </li>
            <li>
              <a href="/#pricing" onClick={closeMenu}>
                Pricing
              </a>
            </li>
            <li>
              <a href="#how-it-works" onClick={closeMenu}>
                How It Works
              </a>
            </li>
            <li>
              <a href="#included" onClick={closeMenu}>
                What's Included
              </a>
            </li>
            <li>
              <a href="#compare" onClick={closeMenu}>
                Compare Plans
              </a>
            </li>
          </ul>
          <Link to="/" className="nav-logo">
            <img src="/logo.png" alt="Agent NexLiFy" />
          </Link>
          <div className="nav-right">
            <a href="/demo" className="nav-login">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                <polyline points="10 17 15 12 10 7" />
                <line x1="15" y1="12" x2="3" y2="12" />
              </svg>
              <span>Try Demo</span>
            </a>
            <Link to="/signup?plan=chatbot" className="nav-cta">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ============ HERO ============ */}
      <section className="hero">
        <div className="container hero-content">
          <div className="hero-badge reveal" ref={revealRef}>
            <span className="hero-badge-dot" aria-hidden="true"></span>
            $19.99/mo {"\u2014"} No setup fee {"\u2014"} Cancel anytime
          </div>
          <h1 className="reveal" ref={revealRef}>
            AI Chatbot for Your Website
            <br />
            <span className="accent">{"\u2014"} Set Up in 5 Minutes</span>
          </h1>
          <p className="hero-sub reveal" ref={revealRef}>
            $19.99/mo. No setup fee. No coding. Cancel anytime.
          </p>
          <div className="hero-buttons reveal" ref={revealRef}>
            <Link to="/signup?plan=chatbot" className="btn-primary">
              Start with Chatbot {"\u2192"}
            </Link>
            <a href="/demo" className="btn-secondary">
              See It In Action {"\u2193"}
            </a>
          </div>
          <p className="hero-note reveal" ref={revealRef}>
            Chatbot plan at $19.99/mo {"\u2014"} upgrade to Agent OS anytime
          </p>
        </div>
      </section>

      {/* ============ SOCIAL PROOF BAR ============ */}
      <div className="proof-bar reveal" ref={revealRef}>
        <div className="container">
          <div className="proof-bar-inner">
            <div className="proof-item">
              <div className="proof-icon" aria-hidden="true">
                &#127970;
              </div>
              100+ Connecticut businesses
            </div>
            <div className="proof-item">
              <div className="proof-icon" aria-hidden="true">
                &#9889;
              </div>
              &lt; 5 min setup
            </div>
            <div className="proof-item">
              <div className="proof-icon" aria-hidden="true">
                &#129302;
              </div>
              24/7 automation
            </div>
            <div className="proof-item">
              <div className="proof-icon" aria-hidden="true">
                &#128736;
              </div>
              No coding
            </div>
          </div>
        </div>
      </div>

      {/* ============ HOW IT WORKS ============ */}
      <section className="section how" id="how-it-works">
        <div className="container">
          <div className="how-header">
            <div className="section-label reveal" ref={revealRef}>
              How It Works
            </div>
            <h2 className="section-title reveal" ref={revealRef}>
              Live on your site in three simple steps.
            </h2>
          </div>
          <div className="how-steps">
            <div className="how-step reveal" ref={revealRef}>
              <div className="how-step-num" aria-hidden="true">
                01
              </div>
              <h3>Sign Up</h3>
              <p>
                Enter your business name and email. No setup fee, no
                commitment {"\u2014"} just your account.
              </p>
            </div>
            <div className="how-step reveal" ref={revealRef}>
              <div className="how-step-num" aria-hidden="true">
                02
              </div>
              <h3>Customize Your Bot</h3>
              <p>
                Set your chatbot's name, greeting message, and brand colors.
                Make it feel like part of your team.
              </p>
            </div>
            <div className="how-step reveal" ref={revealRef}>
              <div className="how-step-num" aria-hidden="true">
                03
              </div>
              <h3>Copy One Line of Code</h3>
              <p>
                Paste a single script tag anywhere on your site {"\u2014"}{" "}
                WordPress, Squarespace, Wix, Shopify, or plain HTML.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ WHAT'S INCLUDED FREE ============ */}
      <section
        className="section"
        id="included"
        style={{ background: "var(--bg-secondary)" }}
      >
        <div className="container">
          <div className="included-header">
            <div className="section-label reveal" ref={revealRef}>
              What's Included
            </div>
            <h2 className="section-title reveal" ref={revealRef}>
              Everything you need to start capturing leads.
            </h2>
            <p className="section-subtitle reveal" ref={revealRef}>
              The Chatbot plan at $19.99/mo includes all of these features with no hidden fees.
            </p>
          </div>
          <div className="included-grid">
            <div className="included-card reveal" ref={revealRef}>
              <div className="included-icon" aria-hidden="true">
                &#128172;
              </div>
              <h3>Unlimited Conversations</h3>
              <p>
                No conversation caps. Capture every lead that
                visits your site after hours or during busy periods.
              </p>
            </div>
            <div className="included-card reveal" ref={revealRef}>
              <div className="included-icon" aria-hidden="true">
                &#129302;
              </div>
              <h3>AI-Powered Responses</h3>
              <p>
                Intelligent answers to customer questions powered by the latest
                AI models. Sounds human, works 24/7.
              </p>
            </div>
            <div className="included-card reveal" ref={revealRef}>
              <div className="included-icon" aria-hidden="true">
                &#127919;
              </div>
              <h3>Automatic Lead Capture</h3>
              <p>
                Captures name, email, and phone number from every conversation.
                Leads go straight to your inbox.
              </p>
            </div>
            <div className="included-card reveal" ref={revealRef}>
              <div className="included-icon" aria-hidden="true">
                &#128197;
              </div>
              <h3>Appointment Booking</h3>
              <p>
                Let visitors schedule appointments directly through the chatbot.
                Syncs with your calendar.
              </p>
            </div>
            <div className="included-card reveal" ref={revealRef}>
              <div className="included-icon" aria-hidden="true">
                &#128231;
              </div>
              <h3>Email Notifications</h3>
              <p>
                Get notified instantly when a new lead comes in so you can
                follow up while they're still warm.
              </p>
            </div>
            <div className="included-card reveal" ref={revealRef}>
              <div className="included-icon" aria-hidden="true">
                &#127775;
              </div>
              <h3>One-Line Install</h3>
              <p>
                Paste a single script tag on any site - WordPress, Wix,
                Squarespace, Shopify, or plain HTML. Live in minutes.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ COMPARISON TABLE ============ */}
      <section className="section comparison" id="compare">
        <div className="container">
          <div className="comparison-header">
            <div className="section-label reveal" ref={revealRef}>
              Compare Plans
            </div>
            <h2 className="section-title reveal" ref={revealRef}>
              Pick the plan that fits your business.
            </h2>
            <p className="section-subtitle reveal" ref={revealRef}>
              Upgrade or downgrade anytime. No setup fees.
            </p>
          </div>
          <div className="comparison-table-wrap reveal" ref={revealRef}>
            <table className="comparison-table">
              <thead>
                <tr>
                  <th></th>
                  <th className="highlight">
                    Chatbot<span className="price-tag">$19.99/mo</span>
                  </th>
                  <th>
                    Agent OS<span className="price-tag">$99.99/mo</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>AI Chat Widget</td>
                  <td className="highlight">
                    <span className="check">&#10003;</span>
                  </td>
                  <td>
                    <span className="check">&#10003;</span>
                  </td>
                </tr>
                <tr>
                  <td>Lead Capture</td>
                  <td className="highlight">
                    <span className="check">&#10003;</span>
                  </td>
                  <td>
                    <span className="check">&#10003;</span>
                  </td>
                </tr>
                <tr>
                  <td>FAQ Training</td>
                  <td className="highlight">
                    <span className="check">&#10003;</span>
                  </td>
                  <td>
                    <span className="check">&#10003;</span>
                  </td>
                </tr>
                <tr>
                  <td>Marketing and SEO Suite</td>
                  <td className="highlight">
                    <span className="dash">{"\u2014"}</span>
                  </td>
                  <td>
                    <span className="check">&#10003;</span>
                  </td>
                </tr>
                <tr>
                  <td>Agent OS (AI Staff)</td>
                  <td className="highlight">
                    <span className="dash">{"\u2014"}</span>
                  </td>
                  <td>
                    <span className="check">&#10003;</span>
                  </td>
                </tr>
                <tr>
                  <td>Social Media and Campaigns</td>
                  <td className="highlight">
                    <span className="dash">{"\u2014"}</span>
                  </td>
                  <td>
                    <span className="check">&#10003;</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p
            style={{ textAlign: "center", marginTop: "32px" }}
            className="reveal"
            ref={revealRef}
          >
            <a
              href="/pricing"
              style={{
                color: "var(--accent)",
                fontWeight: 600,
                fontSize: "16px",
              }}
            >
              See all plans &amp; features {"\u2192"}
            </a>
          </p>
        </div>
      </section>

      {/* ============ CTA ============ */}
      <section className="cta-section" id="cta">
        <div className="container cta-content">
          <h2 className="section-title reveal" ref={revealRef}>
            Ready to Stop Missing Leads?
          </h2>
          <p className="section-subtitle reveal" ref={revealRef}>
            Your next customer could be on your website right now. Give them
            someone to talk to.
          </p>
          <div
            className="hero-buttons reveal"
            ref={revealRef}
            style={{ marginBottom: 0 }}
          >
            <Link
              to="/signup?plan=chatbot"
              className="btn-primary"
              style={{ padding: "18px 40px", fontSize: "18px" }}
            >
              Start with Chatbot {"\u2192"}
            </Link>
          </div>
          <p className="cta-note reveal" ref={revealRef}>
            $19.99/mo. No setup fee. Cancel anytime.
          </p>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <footer className="footer">
        <div className="container">
          <div className="footer-inner">
            <div className="footer-brand">
              <img
                src="/logo.png"
                alt="Agent NexLiFy Logo"
                className="footer-brand-logo"
              />
              <p>AI-powered automation for businesses.</p>
              <Link
                to="/signup?plan=chatbot"
                className="btn-primary"
                style={{
                  marginTop: "16px",
                  fontSize: "14px",
                  padding: "12px 24px",
                }}
              >
                Get Started {"\u2192"}
              </Link>
            </div>
            <div className="footer-col">
              <h4>Product</h4>
              <ul>
                <li>
                  <a href="/#features">Features</a>
                </li>
                <li>
                  <a href="/#pricing">Pricing</a>
                </li>
                <li>
                  <a href="/#faq">FAQ</a>
                </li>
                <li>
                  <Link to="/signup?plan=chatbot">Sign Up</Link>
                </li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>Company</h4>
              <ul>
                <li>
                  <a href="/#why">Why Us</a>
                </li>
                <li>
                  <a href="/#about-us">About</a>
                </li>
                <li>
                  <a href="mailto:hello@agentnexlify.com">Contact</a>
                </li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>Legal</h4>
              <ul>
                <li>
                  <a href="/privacy">Privacy Policy</a>
                </li>
                <li>
                  <a href="/terms">Terms of Service</a>
                </li>
              </ul>
            </div>
          </div>
          <div className="footer-bottom">
            <span className="footer-copy">
              &copy; 2026 Agent NexLiFy. All rights reserved.
            </span>
            {/* Social links removed until real profiles are created */}
          </div>
        </div>
      </footer>
    </>
  );
}
