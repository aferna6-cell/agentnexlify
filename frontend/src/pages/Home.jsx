import React, { useState, useEffect, useCallback, useRef } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import "../styles/home.css";

const CALENDLY_URL = "https://calendly.com/aidanfernandes31/15-minute-agent-nexliffy-demo";

/* Read email from JWT in localStorage (works outside AuthProvider) */
function getUserEmail() {
  try {
    const token = localStorage.getItem("anx_token");
    if (!token) return null;
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;
    return payload.email || null;
  } catch {
    return null;
  }
}

/* Pricing CTA that prefills email or redirects to signup */
function StripeCta({ href, children }) {
  const handleClick = (e) => {
    const email = getUserEmail();
    if (!email) {
      e.preventDefault();
      window.location.href = "/signup";
      return;
    }
    e.preventDefault();
    const url = `${href}?prefilled_email=${encodeURIComponent(email)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };
  return (
    <a href={href} onClick={handleClick} className="pricing-cta">
      {children}
    </a>
  );
}

const faqData = [
  {
    id: "faq-a1",
    question: "What\u2019s included in each plan?",
    answer:
      "Every plan builds on the previous tier. Foundation covers lead capture, reviews, and reminders. Growth adds follow-up sequences, FAQ bot, and CRM. Operations adds AI booking, invoicing, task automation, and lead scoring.",
  },
  {
    id: "faq-a2",
    question: "Do I need any technical skills?",
    answer:
      "Not at all. We handle 100% of the setup, integration, and ongoing management. If you can use email, you can use Agent NexLiFy.",
  },
  {
    id: "faq-a3",
    question: "What tools do you integrate with?",
    answer:
      "Gmail, Outlook, Google Calendar, Calendly, most CRMs (HubSpot, Follow Up Boss, Salesforce), Slack, QuickBooks, and more. If you use it, we can probably connect to it.",
  },
  {
    id: "faq-a4",
    question: "How long does setup take?",
    answer:
      "Most businesses are fully live within 48 hours of our kickoff call. Complex custom workflows may take up to a week.",
  },
  {
    id: "faq-a5",
    question: "Can I upgrade my plan later?",
    answer:
      "Absolutely. Most partners start with Foundation or Growth and upgrade within a few months once they see results. We migrate everything seamlessly \u2014 no downtime, no lost data.",
  },
  {
    id: "faq-a6",
    question: "Is there a contract?",
    answer: "No long-term contracts. Month-to-month billing. Cancel anytime.",
  },
  {
    id: "faq-a7",
    question: "What if AI makes a mistake?",
    answer:
      "You stay in control. Emails are drafted for your approval before sending. The AI qualifies leads \u2014 you decide how to close them. Nothing goes out without your say-so.",
  },
  {
    id: "faq-a8",
    question: "How is this different from Zapier or ChatGPT?",
    answer:
      "Those are tools. You still have to build, manage, and fix everything yourself. Agent NexLiFy is a service. We do the work. You get the results.",
  },
];

export default function Home() {
  const [navScrolled, setNavScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(null);
  const faqRefs = useRef({});
  const isLoggedIn = getUserEmail() !== null;

  useEffect(() => {
    const handleScroll = () => setNavScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  useEffect(() => {
    const reveals = document.querySelectorAll(".landing-page .reveal");
    if (!("IntersectionObserver" in window)) {
      reveals.forEach((el) => el.classList.add("visible"));
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
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const toggleMenu = useCallback(() => setMenuOpen((p) => !p), []);
  const closeMenu = useCallback(() => setMenuOpen(false), []);
  const handleFaqToggle = useCallback((id) => setOpenFaq((p) => (p === id ? null : id)), []);

  const getFaqMaxHeight = useCallback(
    (id) => {
      if (openFaq === id && faqRefs.current[id]) {
        return faqRefs.current[id].scrollHeight + "px";
      }
      return "0";
    },
    [openFaq]
  );

  return (
    <div className="landing-page">
      <Helmet>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Agent NexLiFy | AI Receptionist for Local Businesses</title>
        <meta
          name="description"
          content="Agent NexLiFy is an AI receptionist that answers calls, captures leads, and books appointments for local businesses — 24/7. Set up in under 5 minutes."
        />
        <link rel="canonical" href="https://agentnexlify.com/" />
        <meta property="og:title" content="Agent NexLiFy | AI Receptionist for Local Businesses" />
        <meta
          property="og:description"
          content="Agent NexLiFy is an AI receptionist that answers calls, captures leads, and books appointments for local businesses — 24/7. Set up in under 5 minutes."
        />
        <meta property="og:image" content="https://agentnexlify.com/og-image.png" />
        <meta property="og:url" content="https://agentnexlify.com/" />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Agent NexLiFy | AI Receptionist for Local Businesses" />
        <meta
          name="twitter:description"
          content="Agent NexLiFy is an AI receptionist that answers calls, captures leads, and books appointments for local businesses — 24/7. Set up in under 5 minutes."
        />
        <meta name="twitter:image" content="https://agentnexlify.com/og-image.png" />
        <meta name="google-site-verification" content="87NEEvBU6dL3QuI_1iZK9wgq4Jtws60z1M3bKu-mS6s" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
        <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "AgentNexLiFy",
  "url": "https://agentnexlify.com",
  "logo": "https://agentnexlify.com/logo.png",
  "description": "AI-powered customer service platform for local businesses",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "Clemson",
    "addressRegion": "SC",
    "addressCountry": "US"
  },
  "contactPoint": {
    "@type": "ContactPoint",
    "contactType": "sales",
    "url": "https://agentnexlify.com/contact"
  }
}
        `}</script>
        <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "AgentNexLiFy",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "description": "AI-powered customer service chatbot for local businesses",
  "url": "https://agentnexlify.com",
  "offers": [
    { "@type": "Offer", "name": "Free", "price": "0", "priceCurrency": "USD" },
    {
      "@type": "Offer", "name": "Foundation", "price": "99", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "99", "priceCurrency": "USD", "billingDuration": "P1M" }
    },
    {
      "@type": "Offer", "name": "Growth", "price": "249", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "249", "priceCurrency": "USD", "billingDuration": "P1M" }
    },
    {
      "@type": "Offer", "name": "Operations", "price": "499", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "499", "priceCurrency": "USD", "billingDuration": "P1M" }
    }
  ]
}
        `}</script>
        <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    { "@type": "Question", "name": "What's included in each plan?", "acceptedAnswer": { "@type": "Answer", "text": "Every plan builds on the previous tier. Foundation covers lead capture, reviews, and reminders. Growth adds follow-up sequences, FAQ bot, and CRM. Operations adds AI booking, invoicing, task automation, and lead scoring." } },
    { "@type": "Question", "name": "Do I need any technical skills?", "acceptedAnswer": { "@type": "Answer", "text": "Not at all. We handle 100% of the setup, integration, and ongoing management." } },
    { "@type": "Question", "name": "What tools do you integrate with?", "acceptedAnswer": { "@type": "Answer", "text": "Gmail, Outlook, Google Calendar, Calendly, most CRMs (HubSpot, Follow Up Boss, Salesforce), Slack, QuickBooks, and more." } },
    { "@type": "Question", "name": "How long does setup take?", "acceptedAnswer": { "@type": "Answer", "text": "Most businesses are fully live within 48 hours of our kickoff call." } },
    { "@type": "Question", "name": "Can I upgrade my plan later?", "acceptedAnswer": { "@type": "Answer", "text": "Absolutely. Most partners start with Foundation or Growth and upgrade within a few months." } },
    { "@type": "Question", "name": "Is there a contract?", "acceptedAnswer": { "@type": "Answer", "text": "No long-term contracts. Month-to-month billing. Cancel anytime." } },
    { "@type": "Question", "name": "What if AI makes a mistake?", "acceptedAnswer": { "@type": "Answer", "text": "You stay in control. Emails are drafted for your approval before sending. The AI qualifies leads — you decide how to close them." } },
    { "@type": "Question", "name": "How is this different from Zapier or ChatGPT?", "acceptedAnswer": { "@type": "Answer", "text": "Those are tools you manage yourself. Agent NexLiFy is a done-for-you service." } }
  ]
}
        `}</script>
      </Helmet>

      {/* ============ NAV ============ */}
      <nav className={`lp-nav${navScrolled ? " scrolled" : ""}`} role="navigation" aria-label="Main navigation">
        <div className="lp-nav-inner">
          <a href="#" className="lp-nav-logo">
            <img src="/logo.png" alt="Agent NexLiFy" />
            <span>NexLiFy</span>
          </a>

          <div className={`lp-nav-links${menuOpen ? " open" : ""}`}>
            <a href="#features" onClick={closeMenu}>Features</a>
            <a href="#how-it-works" onClick={closeMenu}>How It Works</a>
            <a href="#pricing" onClick={closeMenu}>Pricing</a>
            <a href="#faq" onClick={closeMenu}>FAQ</a>
          </div>

          <div className="lp-nav-actions">
            {isLoggedIn ? (
              <Link to="/dashboard" className="lp-nav-cta">Dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="lp-nav-login"><span>Log In</span></Link>
                <Link to="/signup" className="lp-nav-cta">Get Started Free</Link>
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

      {/* ============ HERO ============ */}
      <section className="lp-hero">
        <div className="container">
          <div className="lp-hero-inner">
            <div className="lp-hero-text">
              <h1 className="reveal">
                Never Miss a{" "}
                <span className="accent-gradient">Lead</span> Again
              </h1>
              <p className="lp-hero-sub reveal">
                An AI receptionist for your website that answers questions, captures contact info,
                and books appointments — even at 2 AM. Set up in 5 minutes, no coding needed.
              </p>
              <div className="lp-hero-buttons reveal">
                <Link to="/signup" className="btn-primary">
                  Start Free {"\u2192"}
                </Link>
                <a href="#demo" className="btn-secondary">
                  Watch Demo {"\u2193"}
                </a>
              </div>
            </div>

            {/* Animated Widget Mockup */}
            <div className="widget-mockup reveal">
              <div className="widget-mockup-header">
                <div className="widget-mockup-avatar">AI</div>
                <div className="widget-mockup-header-text">
                  <div className="widget-mockup-name">Bright Smile Dental</div>
                  <div className="widget-mockup-status">
                    <span className="widget-mockup-status-dot"></span>
                    Online
                  </div>
                </div>
              </div>
              <div className="widget-mockup-body">
                <div className="wm-msg wm-msg-bot">
                  Hi! Welcome to Bright Smile Dental. I can help you book an appointment, check insurance, or answer any questions.
                </div>
                <div className="wm-msg wm-msg-user">
                  Do you accept Delta Dental insurance?
                </div>
                <div className="wm-typing" aria-hidden="true">
                  <span></span><span></span><span></span>
                </div>
                <div className="wm-msg wm-msg-bot">
                  Yes! We&apos;re in-network with Delta Dental. Would you like to book a cleaning? I have openings this Thursday and Friday.
                </div>
                <div className="wm-form">
                  <div className="wm-form-label">Book your appointment</div>
                  <div className="wm-form-input">Your name</div>
                  <div className="wm-form-input">Phone number</div>
                  <div className="wm-form-btn">Book My Appointment</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ TRUST BAR ============ */}
      <section className="lp-trust">
        <div className="container">
          <p className="lp-trust-label reveal">Works with the tools you already use</p>
          <div className="lp-trust-logos reveal">
            <svg viewBox="0 0 24 24" aria-label="Gmail">
              <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z" />
            </svg>
            <svg viewBox="0 0 24 24" aria-label="Google Calendar">
              <path d="M18.316 5.684H24v12.632h-5.684V5.684zM5.684 24h12.632v-5.684H5.684V24zM18.316 5.684V0H5.684v5.684h12.632zM5.684 18.316H0V5.684h5.684v12.632zM7.953 14.39l1.478-1.149c.543.49 1.142.735 1.797.735.654 0 1.108-.254 1.108-.815 0-.462-.336-.735-1.01-.998l-.736-.287c-1.087-.42-1.621-1.109-1.621-2.098 0-1.314 1.034-2.197 2.507-2.197.922 0 1.72.342 2.274.943l-1.264 1.155c-.385-.336-.77-.504-1.176-.504-.44 0-.748.222-.748.598 0 .368.253.586.849.81l.748.288c1.216.468 1.785 1.108 1.785 2.24 0 1.351-1.064 2.344-2.67 2.344-1.143 0-2.07-.434-2.72-1.264l.4-.8z" />
            </svg>
            <svg viewBox="0 0 24 24" aria-label="HubSpot">
              <path d="M18.164 7.93V5.084a2.198 2.198 0 0 0 1.267-1.984v-.066a2.2 2.2 0 0 0-2.198-2.198h-.066a2.2 2.2 0 0 0-2.198 2.198v.066c0 .865.506 1.61 1.233 1.966v2.862a5.662 5.662 0 0 0-2.905 1.384l-7.666-5.97a2.39 2.39 0 0 0 .072-.563 2.413 2.413 0 1 0-2.413 2.413c.437 0 .842-.122 1.2-.325l7.544 5.876a5.668 5.668 0 0 0-.478 2.279 5.681 5.681 0 0 0 .565 2.47l-2.262 2.263a1.88 1.88 0 0 0-.573-.097 1.902 1.902 0 1 0 1.901 1.901c0-.2-.035-.39-.092-.572l2.235-2.235a5.686 5.686 0 0 0 3.45 1.17h.002a5.69 5.69 0 1 0 0-11.38 5.69 5.69 0 0 0-2.576.612l-.062.033zm.062 8.151h-.002a2.843 2.843 0 1 1 .002 0z" />
            </svg>
            <svg viewBox="0 0 24 24" aria-label="Salesforce">
              <path d="M10.006 5.415a4.195 4.195 0 0 1 3.045-1.306c1.56 0 2.954.9 3.69 2.205a4.89 4.89 0 0 1 2.013-.432c2.735 0 4.952 2.23 4.952 4.98s-2.217 4.98-4.952 4.98a4.937 4.937 0 0 1-.765-.06 3.469 3.469 0 0 1-3.089 1.913 3.469 3.469 0 0 1-1.48-.332 4.14 4.14 0 0 1-3.783 2.47 4.14 4.14 0 0 1-3.682-2.25 3.596 3.596 0 0 1-.61.053c-1.987 0-3.598-1.62-3.598-3.618a3.61 3.61 0 0 1 1.487-2.918A4.39 4.39 0 0 1 3 9.09c0-2.442 1.976-4.42 4.414-4.42 1.466 0 2.632.604 3.592 1.745z" />
            </svg>
            <svg viewBox="0 0 24 24" aria-label="Slack">
              <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.122 2.521a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.268 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zm-2.523 10.122a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.268a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
            </svg>
            <svg viewBox="0 0 24 24" aria-label="QuickBooks">
              <path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zm5.723 16.17h-1.807c0 1.268-1.027 2.297-2.294 2.297v-1.81c0-2.049-.006-4.098.003-6.147.003-.596-.003-1.057-.699-1.286-.938-.31-1.89.37-1.89 1.382.004 2.037.001 4.074.002 6.11v1.75h-1.81c0 1.268-1.026 2.297-2.293 2.297V7.833h1.81c0-1.27 1.026-2.297 2.293-2.297v1.81c0 2.048.006 4.097-.003 6.146-.003.596.003 1.058.699 1.287.938.309 1.89-.371 1.89-1.383-.004-2.037-.001-4.074-.002-6.11v-1.75h1.808c0-1.27 1.026-2.298 2.293-2.298V16.17z" />
            </svg>
          </div>
        </div>
      </section>

      {/* ============ HOW IT WORKS ============ */}
      <section className="section" id="how-it-works">
        <div className="container">
          <div className="lp-how-header">
            <div className="section-label reveal">How It Works</div>
            <h2 className="section-title reveal">Live on your website in 5 minutes.</h2>
          </div>
          <div className="lp-how-steps">
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">1</div>
              <h3>Paste One Line of Code</h3>
              <p>
                Add a single script tag to your site. Works with WordPress, Squarespace, Wix, or any website.
              </p>
            </div>
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">2</div>
              <h3>AI Answers, Captures, Books</h3>
              <p>
                Your AI receptionist greets every visitor, answers FAQs, collects contact info, and books appointments — automatically.
              </p>
            </div>
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">3</div>
              <h3>You Close Deals</h3>
              <p>
                Qualified leads are delivered straight to your dashboard with full conversation
                history, contact info, and AI-generated scores.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ FEATURES ============ */}
      <section className="section" id="features" style={{ background: "var(--bg-secondary)" }}>
        <div className="container">
          <div className="lp-features-header">
            <div className="section-label reveal">Features</div>
            <h2 className="section-title reveal">Everything your front desk does — without the front desk.</h2>
            <p className="section-subtitle reveal">
              Six tools that work 24/7 so you can focus on the work that matters.
            </p>
          </div>
          <div className="lp-features-grid">
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <h3>AI Chat Widget</h3>
              <p>Greets every website visitor instantly. Answers their questions, captures their info, and hands you a qualified lead.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              </div>
              <h3>Lead Capture</h3>
              <p>Collects name, email, and phone from every visitor — then pings you instantly so you can follow up while they&apos;re still interested.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
              </div>
              <h3>Smart Follow-Up</h3>
              <p>Sends personalized email and SMS sequences automatically. Turns &ldquo;maybe later&rdquo; into booked appointments.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <h3>FAQ Bot</h3>
              <p>Trained on your business. Answers the same 20 questions you get every day — so you don&apos;t have to.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              </div>
              <h3>Appointment Booking</h3>
              <p>Books appointments, sends reminders, and handles reschedules. Syncs with Google Calendar so nothing falls through the cracks.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              </div>
              <h3>Lead Scoring</h3>
              <p>Ranks every lead by buying intent. Alerts you the moment someone is ready to close — so you call them first.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ DEMO ============ */}
      <section className="section lp-demo" id="demo">
        <div className="container">
          <div className="lp-demo-inner">
            <div className="section-label reveal">See It In Action</div>
            <h2 className="section-title reveal">See it work on a real website.</h2>
            <p className="section-subtitle reveal">
              Watch how a dental office uses Agent NexLiFy to book appointments and capture leads around the clock.
            </p>
            <div className="lp-demo-cta-block reveal">
              <a href={CALENDLY_URL} className="btn-primary" target="_blank" rel="noopener noreferrer">
                Book a Live Demo {"\u2192"}
              </a>
              <Link to="/free-widget" className="btn-secondary">
                Or try the free version on your site {"\u2192"}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ============ PRICING ============ */}
      <section className="section" id="pricing">
        <div className="container">
          <div className="lp-pricing-header">
            <div className="section-label reveal">Pricing</div>
            <h2 className="section-title reveal">Simple pricing. Serious ROI.</h2>
            <p className="section-subtitle reveal">
              Every plan includes hands-on setup, onboarding, and ongoing support from our team.
            </p>
          </div>
          <div className="lp-pricing-grid">
            {/* Free */}
            <div className="lp-pricing-card reveal">
              <div className="lp-pricing-plan-name">Free</div>
              <div className="lp-pricing-tagline">See it work on your site.</div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$0</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">No credit card required</div>
              <div className="lp-pricing-divider"></div>
              <ul className="lp-pricing-features">
                <li>Up to 50 conversations/month</li>
                <li>AI chatbot widget</li>
                <li>Lead capture form</li>
                <li>Easy one-line install</li>
              </ul>
              <Link to="/signup" className="pricing-cta">
                Get Started {"\u2192"}
              </Link>
            </div>

            {/* Foundation */}
            <div className="lp-pricing-card reveal">
              <div className="lp-pricing-plan-name">Foundation</div>
              <div className="lp-pricing-tagline">Stop losing leads to voicemail.</div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$99</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">$149 one-time setup</div>
              <div className="lp-pricing-divider"></div>
              <ul className="lp-pricing-features">
                <li>Unlimited conversations</li>
                <li>Lead capture &amp; instant alerts</li>
                <li>Automated review requests</li>
                <li>Missed call text-back</li>
                <li>Appointment reminders</li>
              </ul>
              <StripeCta href="https://buy.stripe.com/test_7sYdRb4CedaQaxk2J14AU01">
                Get Started {"\u2192"}
              </StripeCta>
            </div>

            {/* Growth — Popular */}
            <div className="lp-pricing-card popular reveal">
              <div className="lp-pricing-plan-name">Growth</div>
              <div className="lp-pricing-tagline">Your highest-ROI employee.</div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$249</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">$399 one-time setup</div>
              <div className="lp-pricing-divider"></div>
              <div className="lp-pricing-includes">Everything in Foundation, plus:</div>
              <ul className="lp-pricing-features">
                <li>Automated follow-up sequences</li>
                <li>AI FAQ &amp; support bot</li>
                <li>Quote &amp; estimate automation</li>
                <li>CRM setup &amp; pipeline</li>
                <li>Priority support</li>
              </ul>
              <StripeCta href="https://buy.stripe.com/test_7sYdRb7Oq1s8gVIabt4AU02">
                Get Started {"\u2192"}
              </StripeCta>
            </div>

            {/* Operations */}
            <div className="lp-pricing-card reveal">
              <div className="lp-pricing-plan-name">Operations</div>
              <div className="lp-pricing-tagline">Cut admin work in half.</div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$499</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">$599 one-time setup</div>
              <div className="lp-pricing-divider"></div>
              <div className="lp-pricing-includes">Everything in Growth, plus:</div>
              <ul className="lp-pricing-features">
                <li>AI appointment booking agent</li>
                <li>Invoice &amp; payment follow-up</li>
                <li>Internal task automation</li>
                <li>AI lead scoring &amp; alerts</li>
                <li>Dedicated account manager</li>
              </ul>
              <StripeCta href="https://buy.stripe.com/test_8x24gBfgSc6M6h41EX4AU03">
                Get Started {"\u2192"}
              </StripeCta>
            </div>
          </div>
          <p className="lp-pricing-footer-note reveal">
            All plans include done-for-you setup, onboarding, and ongoing optimization. Cancel anytime.
          </p>
        </div>
      </section>

      {/* ============ FAQ ============ */}
      <section className="section lp-faq" id="faq">
        <div className="container">
          <div className="lp-faq-header">
            <h2 className="section-title reveal">Questions? We&apos;ve got answers.</h2>
          </div>
          <div className="lp-faq-list reveal" role="list">
            {faqData.map((item) => (
              <div className="lp-faq-item" role="listitem" key={item.id}>
                <button
                  className="lp-faq-question"
                  aria-expanded={openFaq === item.id ? "true" : "false"}
                  aria-controls={item.id}
                  onClick={() => handleFaqToggle(item.id)}
                >
                  {item.question}
                  <svg
                    className="lp-faq-chevron"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </button>
                <div
                  className="lp-faq-answer"
                  id={item.id}
                  role="region"
                  ref={(el) => { faqRefs.current[item.id] = el; }}
                  style={{ maxHeight: getFaqMaxHeight(item.id) }}
                >
                  <div className="lp-faq-answer-inner">{item.answer}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ FINAL CTA ============ */}
      <section className="lp-cta-section" id="cta">
        <div className="container lp-cta-content">
          <h2 className="section-title reveal">Your competitors are already using AI. Are you?</h2>
          <p className="section-subtitle reveal">
            Start capturing leads today with our free AI receptionist. No credit card required.
          </p>
          <div className="lp-cta-buttons reveal">
            <Link to="/signup" className="btn-primary">
              Start Free {"\u2192"}
            </Link>
            <a href={CALENDLY_URL} className="btn-secondary" target="_blank" rel="noopener noreferrer">
              Book a Demo
            </a>
          </div>
          <p className="lp-cta-note reveal">Free forever plan. No credit card. Cancel anytime.</p>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <footer className="lp-footer">
        <div className="container">
          <div className="lp-footer-inner">
            <div className="lp-footer-brand">
              <img src="/logo.png" alt="Agent NexLiFy Logo" className="lp-footer-brand-logo" />
              <p>AI-powered lead capture and automation for local businesses.</p>
            </div>
            <div className="lp-footer-col">
              <h4>Product</h4>
              <ul>
                <li><a href="#features">Features</a></li>
                <li><a href="#pricing">Pricing</a></li>
                <li><a href="#faq">FAQ</a></li>
                <li><Link to="/free-widget">Free AI Widget</Link></li>
              </ul>
            </div>
            <div className="lp-footer-col">
              <h4>Company</h4>
              <ul>
                <li><a href="#how-it-works">How It Works</a></li>
                <li><Link to="/contact">Contact</Link></li>
                <li><a href={CALENDLY_URL} target="_blank" rel="noopener noreferrer">Book a Demo</a></li>
              </ul>
            </div>
            <div className="lp-footer-col">
              <h4>Legal</h4>
              <ul>
                <li><Link to="/privacy">Privacy Policy</Link></li>
                <li><Link to="/terms">Terms of Service</Link></li>
              </ul>
            </div>
          </div>
          <div className="lp-footer-bottom">
            <span className="lp-footer-copy">&copy; 2026 Agent NexLiFy. All rights reserved.</span>
            <div className="lp-footer-socials">
              <a href="#" aria-label="Twitter / X">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
              <a href="#" aria-label="LinkedIn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
