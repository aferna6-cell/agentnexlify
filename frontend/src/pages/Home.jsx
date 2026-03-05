import React, { useState, useEffect, useCallback, useRef } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { trackEvent } from "../utils/analytics";
import "../styles/home.css";

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
    trackEvent("begin_checkout", { event_label: "home_pricing" });
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
        <title>Agent NexLiFy | AI That Runs Your Front Desk</title>
        <meta
          name="description"
          content="Capture leads, book appointments, and follow up with customers — automatically. AI built for local businesses."
        />
        <link rel="canonical" href="https://agentnexlify.com/" />
        <meta property="og:title" content="Agent NexLiFy | AI That Runs Your Front Desk" />
        <meta
          property="og:description"
          content="Capture leads, book appointments, and follow up with customers — automatically. AI built for local businesses."
        />
        <meta property="og:image" content="https://agentnexlify.com/og-image.png" />
        <meta property="og:url" content="https://agentnexlify.com/" />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Agent NexLiFy | AI That Runs Your Front Desk" />
        <meta
          name="twitter:description"
          content="Capture leads, book appointments, and follow up with customers — automatically. AI built for local businesses."
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
  "description": "AI that runs your front desk. Built for local businesses.",
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
  "description": "AI that runs your front desk. Built for local businesses.",
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
            <a href="#pricing" onClick={closeMenu}>Pricing</a>
            <a href="#faq" onClick={closeMenu}>FAQ</a>
          </div>

          <div className="lp-nav-actions">
            {isLoggedIn ? (
              <Link to="/dashboard" className="lp-nav-cta">Dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="lp-nav-login"><span>Log In</span></Link>
                <Link to="/signup" className="lp-nav-cta">Get Started</Link>
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
                AI That Runs Your{" "}
                <span className="accent-gradient">Front Desk</span>
              </h1>
              <p className="lp-hero-sub reveal">
                Capture leads, book appointments, and follow up with customers &mdash; automatically.
              </p>
              <div className="lp-hero-buttons reveal">
                <Link to="/signup" className="btn-primary">
                  Get Started {"\u2192"}
                </Link>
                <Link to="/contact" className="btn-secondary">
                  Book a Demo
                </Link>
              </div>
            </div>

            {/* Animated Widget Mockup */}
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
                  <span></span><span></span><span></span>
                </div>
                <div className="wm-msg wm-msg-bot">
                  I&apos;d love to help! Could I get your name?
                </div>
                <div className="wm-msg wm-msg-user">
                  Sarah Johnson
                </div>
                <div className="wm-msg wm-msg-bot">
                  Thanks Sarah! Let me check availability for Saturday...
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ FEATURES ============ */}
      <section className="section" id="features" style={{ background: "var(--bg-secondary)" }}>
        <div className="container">
          <div className="lp-features-header">
            <h2 className="section-title reveal">Everything your front desk needs.</h2>
          </div>
          <div className="lp-features-grid">
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <h3>Lead Capture</h3>
              <p>Never miss a lead. Your website works 24/7, even when you don&apos;t.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              </div>
              <h3>Appointment Booking</h3>
              <p>Book appointments while you sleep. No more back-and-forth.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
              </div>
              <h3>Smart Follow-Ups</h3>
              <p>Automatic follow-ups that turn &ldquo;maybe&rdquo; into &ldquo;yes.&rdquo;</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <h3>Customer Q&amp;A</h3>
              <p>Instant answers to customer questions, day or night.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              </div>
              <h3>Lead Pipeline</h3>
              <p>Every lead scored and organized. Know who&apos;s ready to buy.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              </div>
              <h3>Email Sequences</h3>
              <p>Hands-free email campaigns that keep your leads warm.</p>
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
              <div className="lp-pricing-tagline">See what AI can do for your business.</div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$0</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">No credit card required</div>
              <div className="lp-pricing-divider"></div>
              <ul className="lp-pricing-features">
                <li>AI chat widget</li>
                <li>Lead capture</li>
                <li>Up to 50 conversations/month</li>
                <li>Basic dashboard</li>
                <li>Email notifications</li>
                <li>Widget customization</li>
                <li>FAQ knowledge base</li>
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
            All plans include done-for-you setup and onboarding. Cancel anytime.
          </p>
        </div>
      </section>

      {/* ============ FAQ ============ */}
      <section className="section lp-faq" id="faq">
        <div className="container">
          <div className="lp-faq-header">
            <h2 className="section-title reveal">FAQ</h2>
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
          <h2 className="section-title reveal">Ready to stop missing leads?</h2>
          <div className="lp-cta-buttons reveal">
            <Link to="/signup" className="btn-primary">
              Get Started {"\u2192"}
            </Link>
            <Link to="/contact" className="btn-secondary">
              Book a Demo
            </Link>
          </div>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <footer className="lp-footer">
        <div className="container">
          <div className="lp-footer-inner">
            <div className="lp-footer-brand">
              <img src="/logo.png" alt="Agent NexLiFy Logo" className="lp-footer-brand-logo" />
              <p>AI that runs your front desk. Built for local businesses.</p>
            </div>
            <div className="lp-footer-col">
              <h4>Product</h4>
              <ul>
                <li><a href="#features">Features</a></li>
                <li><a href="#pricing">Pricing</a></li>
                <li><a href="#faq">FAQ</a></li>
              </ul>
            </div>
            <div className="lp-footer-col">
              <h4>Company</h4>
              <ul>
                <li><Link to="/contact">Contact</Link></li>
                <li><Link to="/contact">Book a Demo</Link></li>
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
