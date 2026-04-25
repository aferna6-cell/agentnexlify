import { useState, useEffect, useCallback, useRef } from "react";
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

/* Pricing CTA that creates a Stripe checkout session or redirects to signup */
function StripeCta({ plan, children }) {
  const handleClick = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("anx_token");
    if (!token) {
      window.location.href = `/signup?plan=${encodeURIComponent(plan)}`;
      return;
    }
    trackEvent("begin_checkout", { event_label: "home_pricing", plan });
    try {
      const API =
        import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";
      const resp = await fetch(`${API}/api/v1/auth/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plan }),
      });
      const data = await resp.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        window.location.href = "/signup";
      }
    } catch {
      window.location.href = "/signup";
    }
  };
  return (
    <a href="/signup" onClick={handleClick} className="pricing-cta">
      {children}
    </a>
  );
}

const faqData = [
  {
    id: "faq-a1",
    question: "What\u2019s included in each plan?",
    answer:
      "Every plan builds on the previous tier. Free includes the chat widget, customer capture, and FAQ knowledge base. Growth starts at $99/month and includes a 7-day free trial, booking, SMS, automation, basic SEO audit, and the AI content writer. Professional is $150/month with the full SEO suite, social media marketing, email/SMS campaigns, and advanced analytics. Enterprise is $250/month with AI visibility tracking, competitor analysis, team accounts, webhooks, and white-label branding.",
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
      "Google Calendar (built-in), plus outbound webhooks to connect with Zapier, Slack, HubSpot, and 5,000+ other tools. We also integrate with Twilio for SMS and Stripe for payments.",
  },
  {
    id: "faq-a5",
    question: "Can I upgrade my plan later?",
    answer:
      "Absolutely! Start with our free plan or Growth and upgrade as your business scales. You can change your plan anytime from the Billing page.",
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
      "You stay in control. Emails are drafted for your approval before sending. Your AI assistant helps identify promising customers - you decide how to follow up. Nothing goes out without your approval.",
  },
  {
    id: "faq-a8",
    question: "How is this different from Zapier or ChatGPT?",
    answer:
      "Those are tools you have to build and manage yourself. Agent NexLiFy is a done-for-you service. We take care of the setup and management so you can focus on your business.",
  },
];

/* ── Demo slideshow tabs ── */
const demoTabs = [
  "Dashboard",
  "Widget Chat",
  "Clients",
  "Automations",
  "Calendar",
];

function DemoSlide({ tab }) {
  if (tab === "Dashboard")
    return (
      <div className="ds-dashboard">
        <div className="ds-stats-row">
          <div className="ds-stat-card">
            <span className="ds-stat-num">24</span>
            <span className="ds-stat-lbl">Leads today</span>
          </div>
          <div className="ds-stat-card">
            <span className="ds-stat-num">8</span>
            <span className="ds-stat-lbl">Appointments</span>
          </div>
          <div className="ds-stat-card accent">
            <span className="ds-stat-num">96%</span>
            <span className="ds-stat-lbl">Response rate</span>
          </div>
        </div>
        <div className="ds-cols">
          <div className="ds-pipeline">
            <div className="ds-panel-title">Lead Pipeline</div>
            <div className="ds-lead">
              <span className="ds-dot green" />
              <span>Sarah Johnson</span>
              <span className="ds-tag hot">Hot</span>
            </div>
            <div className="ds-lead">
              <span className="ds-dot blue" />
              <span>Mike Chen</span>
              <span className="ds-tag warm">Warm</span>
            </div>
            <div className="ds-lead">
              <span className="ds-dot green" />
              <span>Emily Davis</span>
              <span className="ds-tag new">New</span>
            </div>
          </div>
          <div className="ds-activity">
            <div className="ds-panel-title">Recent Activity</div>
            <div className="ds-activity-item">
              <span className="ds-activity-dot" />
              New lead captured from website
            </div>
            <div className="ds-activity-item">
              <span className="ds-activity-dot" />
              Follow-up sent to Sarah Johnson
            </div>
            <div className="ds-activity-item">
              <span className="ds-activity-dot" />
              Appointment booked - Mike Chen
            </div>
          </div>
        </div>
      </div>
    );

  if (tab === "Widget Chat")
    return (
      <div className="ds-chat">
        <div className="ds-chat-window">
          <div className="ds-chat-header">
            <span className="ds-chat-status" />
            AI Assistant - Online
          </div>
          <div className="ds-chat-body">
            <div className="ds-msg bot">Hi! How can I help you today?</div>
            <div className="ds-msg user">
              I&apos;d like to schedule a consultation
            </div>
            <div className="ds-msg bot">
              Of course! I&apos;d be happy to help. What day works best for you?
            </div>
            <div className="ds-msg user">How about Thursday at 2pm?</div>
            <div className="ds-msg bot">
              Thursday at 2:00 PM is available. I&apos;ve booked that for you.
              You&apos;ll get a confirmation email shortly!
            </div>
          </div>
          <div className="ds-chat-input">
            <span>Type a message...</span>
          </div>
        </div>
      </div>
    );

  if (tab === "Clients")
    return (
      <div className="ds-clients">
        <div className="ds-panel-title">Clients &amp; Leads</div>
        <div className="ds-table">
          <div className="ds-table-head">
            <span>Name</span>
            <span>Score</span>
            <span>Stage</span>
            <span>Last Contact</span>
          </div>
          <div className="ds-table-row">
            <span>Sarah Johnson</span>
            <span className="ds-score high">92</span>
            <span className="ds-tag hot">Hot</span>
            <span>2 hrs ago</span>
          </div>
          <div className="ds-table-row">
            <span>Mike Chen</span>
            <span className="ds-score med">74</span>
            <span className="ds-tag warm">Warm</span>
            <span>1 day ago</span>
          </div>
          <div className="ds-table-row">
            <span>Emily Davis</span>
            <span className="ds-score high">88</span>
            <span className="ds-tag new">New</span>
            <span>Just now</span>
          </div>
          <div className="ds-table-row">
            <span>James Wilson</span>
            <span className="ds-score low">45</span>
            <span className="ds-tag cold">Cold</span>
            <span>5 days ago</span>
          </div>
          <div className="ds-table-row">
            <span>Lisa Park</span>
            <span className="ds-score med">67</span>
            <span className="ds-tag warm">Warm</span>
            <span>3 hrs ago</span>
          </div>
        </div>
      </div>
    );

  if (tab === "Automations")
    return (
      <div className="ds-automations">
        <div className="ds-panel-title">Email Sequence: New Lead Follow-Up</div>
        <div className="ds-sequence">
          <div className="ds-step active">
            <div className="ds-step-badge">1</div>
            <div className="ds-step-info">
              <strong>Welcome Email</strong>
              <span>Sent immediately</span>
            </div>
            <span className="ds-step-status sent">Sent</span>
          </div>
          <div className="ds-step-line" />
          <div className="ds-step active">
            <div className="ds-step-badge">2</div>
            <div className="ds-step-info">
              <strong>Case Study</strong>
              <span>After 2 days</span>
            </div>
            <span className="ds-step-status sent">Sent</span>
          </div>
          <div className="ds-step-line" />
          <div className="ds-step current">
            <div className="ds-step-badge pulse">3</div>
            <div className="ds-step-info">
              <strong>Check-In</strong>
              <span>After 5 days</span>
            </div>
            <span className="ds-step-status pending">Pending</span>
          </div>
          <div className="ds-step-line dim" />
          <div className="ds-step dim">
            <div className="ds-step-badge">4</div>
            <div className="ds-step-info">
              <strong>Special Offer</strong>
              <span>After 10 days</span>
            </div>
            <span className="ds-step-status">Scheduled</span>
          </div>
        </div>
      </div>
    );

  if (tab === "Calendar")
    return (
      <div className="ds-calendar">
        <div className="ds-panel-title">This Week - March 2026</div>
        <div className="ds-cal-grid">
          {["Mon", "Tue", "Wed", "Thu", "Fri"].map((day) => (
            <div className="ds-cal-col" key={day}>
              <div className="ds-cal-day">{day}</div>
              <div className="ds-cal-slots">
                {day === "Mon" && (
                  <>
                    <div className="ds-cal-event blue">9:00 - Sarah J.</div>
                    <div className="ds-cal-event green">2:00 - Mike C.</div>
                  </>
                )}
                {day === "Tue" && (
                  <div className="ds-cal-event purple">10:30 - Emily D.</div>
                )}
                {day === "Wed" && (
                  <>
                    <div className="ds-cal-event blue">11:00 - James W.</div>
                    <div className="ds-cal-event green">3:30 - Lisa P.</div>
                  </>
                )}
                {day === "Thu" && (
                  <div className="ds-cal-event accent">2:00 - New Consult</div>
                )}
                {day === "Fri" && (
                  <div className="ds-cal-event blue">9:30 - Follow-up</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );

  return null;
}

function DemoPreview() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const iv = setInterval(
      () => setActive((p) => (p + 1) % demoTabs.length),
      5000,
    );
    return () => clearInterval(iv);
  }, []);

  return (
    <section className="section lp-demo-preview" id="demo">
      <div className="container">
        <div className="demo-preview-wrap">
          <div className="demo-browser">
            <div className="demo-browser-bar">
              <span className="demo-dot" />
              <span className="demo-dot" />
              <span className="demo-dot" />
              <span className="demo-url">
                app.agentnexlify.com/
                {demoTabs[active].toLowerCase().replace(/ /g, "-")}
              </span>
            </div>
            <div className="demo-screen">
              <div className="demo-sidebar">
                <div className="demo-sidebar-logo">NexLiFy</div>
                {demoTabs.map((t, i) => (
                  <button
                    key={t}
                    className={`demo-sidebar-item${i === active ? " active" : ""}`}
                    onClick={() => setActive(i)}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="demo-main">
                <div className="ds-slide-wrap">
                  {demoTabs.map((t, i) => (
                    <div
                      key={t}
                      className={`ds-slide${i === active ? " ds-slide-active" : ""}`}
                    >
                      <DemoSlide tab={t} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          {/* Slide indicator dots */}
          <div className="demo-indicators">
            {demoTabs.map((t, i) => (
              <button
                key={t}
                className={`demo-ind${i === active ? " active" : ""}`}
                onClick={() => setActive(i)}
                aria-label={t}
              />
            ))}
          </div>
        </div>
        <div className="demo-preview-cta reveal">
          <div className="section-label">Demo</div>
          <h2 className="section-title">Try Our Demo</h2>
          <Link to="/demo" className="btn-primary">
            Book a Demo {"\u2192"}
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const [navScrolled, setNavScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(null);
  const [showFloatingCta, setShowFloatingCta] = useState(false);
  const [floatingCtaDismissed, setFloatingCtaDismissed] = useState(
    () => sessionStorage.getItem("anx_cta_dismissed") === "1",
  );
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
    return () => {
      document.body.style.overflow = "";
    };
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
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    );
    reveals.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (floatingCtaDismissed) return;
    const showTimer = setTimeout(() => setShowFloatingCta(true), 3000);
    const handleScroll = () => {
      const pricing = document.getElementById("pricing");
      if (pricing) {
        const rect = pricing.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom > 0) {
          setShowFloatingCta(false);
        } else if (!floatingCtaDismissed) {
          setShowFloatingCta(true);
        }
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      clearTimeout(showTimer);
      window.removeEventListener("scroll", handleScroll);
    };
  }, [floatingCtaDismissed]);

  const toggleMenu = useCallback(() => setMenuOpen((p) => !p), []);
  const closeMenu = useCallback(() => setMenuOpen(false), []);
  const dismissFloatingCta = useCallback(() => {
    setShowFloatingCta(false);
    setFloatingCtaDismissed(true);
    sessionStorage.setItem("anx_cta_dismissed", "1");
  }, []);
  const handleFaqToggle = useCallback(
    (id) => setOpenFaq((p) => (p === id ? null : id)),
    [],
  );

  const getFaqMaxHeight = useCallback(
    (id) => {
      if (openFaq === id && faqRefs.current[id]) {
        return faqRefs.current[id].scrollHeight + "px";
      }
      return "0";
    },
    [openFaq],
  );

  return (
    <div className="landing-page">
      <Helmet>
        <link rel="canonical" href="https://agentnexlify.com/" />
        <meta
          name="google-site-verification"
          content="87NEEvBU6dL3QuI_1iZK9wgq4Jtws60z1M3bKu-mS6s"
        />
        <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "AgentNexLiFy",
  "url": "https://agentnexlify.com",
  "logo": "https://agentnexlify.com/logo.png",
  "description": "Your 24/7 AI employee that answers customers, captures leads, books appointments, and follows up automatically.",
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
  "description": "AI-powered business automation platform.",
  "url": "https://agentnexlify.com",
  "offers": [
    { "@type": "Offer", "name": "Free", "price": "0", "priceCurrency": "USD" },
    { "@type": "Offer", "name": "Growth", "price": "99", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "99", "priceCurrency": "USD", "billingDuration": "P1M" }
    },
    {
      "@type": "Offer", "name": "Professional", "price": "150", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "150", "priceCurrency": "USD", "billingDuration": "P1M" }
    },
    {
      "@type": "Offer", "name": "Enterprise", "price": "250", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "250", "priceCurrency": "USD", "billingDuration": "P1M" }
    }
  ]
}
        `}</script>
        <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    { "@type": "Question", "name": "What's included in each plan?", "acceptedAnswer": { "@type": "Answer", "text": "Every plan builds on the previous tier. Free includes the chat widget, customer capture, and FAQ knowledge base. Growth starts at $99/month and includes a 7-day free trial, booking, SMS, automation, basic SEO audit, and the AI content writer. Professional is $150/month with the full SEO suite, social media marketing, email/SMS campaigns, and advanced analytics. Enterprise is $250/month with AI visibility tracking, competitor analysis, team accounts, webhooks, and white-label branding." } },
    { "@type": "Question", "name": "Do I need any technical skills?", "acceptedAnswer": { "@type": "Answer", "text": "Not at all. We handle 100% of the setup, integration, and ongoing management." } },
    { "@type": "Question", "name": "What tools do you integrate with?", "acceptedAnswer": { "@type": "Answer", "text": "Google Calendar (built-in), plus outbound webhooks to connect with Zapier, Slack, HubSpot, and 5,000+ other tools. We also integrate with Twilio for SMS and Stripe for payments." } },

    { "@type": "Question", "name": "Can I upgrade my plan later?", "acceptedAnswer": { "@type": "Answer", "text": "Absolutely! We suggest starting with Growth and upgrading within a few months as your business scales. You can change your plan anytime from the Billing page." } },
    { "@type": "Question", "name": "Is there a contract?", "acceptedAnswer": { "@type": "Answer", "text": "No long-term contracts. Month-to-month billing. Cancel anytime." } },
    { "@type": "Question", "name": "What if AI makes a mistake?", "acceptedAnswer": { "@type": "Answer", "text": "You stay in control. Emails are drafted for your approval before sending. Your AI assistant helps identify promising customers - you decide how to follow up." } },
    { "@type": "Question", "name": "How is this different from Zapier or ChatGPT?", "acceptedAnswer": { "@type": "Answer", "text": "Those are tools you have to build and manage yourself. Agent NexLiFy is a done-for-you service." } }
  ]
}
        `}</script>
      </Helmet>

      {/* ============ NAV ============ */}
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

      {/* ============ HERO ============ */}
      <section className="lp-hero">
        <div className="container">
          <div className="lp-hero-inner">
            <div className="lp-hero-text">
              <h1 className="reveal">
                your hardest working employee that dosen't stop. It answers,
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
                  Embed widget free {"\u2192"}
                </Link>
                <a href="#how-it-works" className="btn-secondary">
                  See how it works
                </a>
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

      {/* ============ HOW IT WORKS ============ */}
      <section className="section" id="how-it-works">
        <div className="container">
          <div className="lp-how-header">
            <div className="section-label reveal">How It Works</div>
            <h2 className="section-title reveal">
              Easy setup in 3 simple steps.
            </h2>
          </div>
          <div className="lp-how-steps">
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">1</div>
              <h3>Tell Us About Your Business</h3>
              <p>
                Answer a few quick questions about your services, hours, and
                what you want customers to know.
              </p>
            </div>
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">2</div>
              <h3>Add the Widget</h3>
              <p>
                Place the chat widget on your site. We can help with the
                install, and you do not need to learn new software.
              </p>
            </div>
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">3</div>
              <h3>Start Helping Customers</h3>
              <p>
                Your assistant starts answering, collecting leads, and following
                up around the clock. You can review everything anytime.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ FEATURES ============ */}
      <section
        className="section"
        id="features"
        style={{ background: "var(--bg-secondary)" }}
      >
        <div className="container">
          <div className="lp-features-header">
            <div className="section-label reveal">Features</div>
            <h2 className="section-title reveal">
              Automate your workflows or grow your marketing - one platform
              handles both.
            </h2>
          </div>
          <div className="lp-features-grid">
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  <line x1="11" y1="8" x2="11" y2="14" />
                  <line x1="8" y1="11" x2="14" y2="11" />
                </svg>
              </div>
              <h3>SEO Audit and Optimization</h3>
              <p>
                Identify what&apos;s holding your site back and get clear steps
                to improve your rankings.
              </p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                </svg>
              </div>
              <h3>AI Content Writer</h3>
              <p>
                Create blogs, social posts, and marketing content in minutes.
              </p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                  <polyline points="16 6 12 2 8 6" />
                  <line x1="12" y1="2" x2="12" y2="15" />
                </svg>
              </div>
              <h3>Social Media Marketing</h3>
              <p>
                Plan, schedule, and manage your social presence across
                platforms.
              </p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
              </div>
              <h3>Email and SMS Campaigns</h3>
              <p>
                Reach the right people at the right time with targeted
                campaigns.
              </p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <h3>Customer Capture</h3>
              <p>
                Never miss a lead. Your website engages visitors and captures
                interest 24/7.
              </p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
              </div>
              <h3>Appointment Booking</h3>
              <p>Let customers book instantly without the back and forth.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </div>
              <h3>Customer Pipeline</h3>
              <p>
                All your leads in one place, scored and organized so you know
                who to focus on.
              </p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="20" x2="18" y2="10" />
                  <line x1="12" y1="20" x2="12" y2="4" />
                  <line x1="6" y1="20" x2="6" y2="14" />
                </svg>
              </div>
              <h3>Analytics and Reporting</h3>
              <p>Track leads, conversions, and performance in real time.</p>
            </div>
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                </svg>
              </div>
              <h3>Hosted Business Page</h3>
              <p>Launch a professional online presence in minutes.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ PRICING ============ */}
      <section className="section" id="pricing">
        <div className="container">
          <div className="lp-pricing-header">
            <div className="section-label reveal">Pricing</div>
            <h2 className="section-title reveal">
              One platform. Every tool your business needs.
            </h2>
            <p className="section-subtitle reveal">
              CRM, marketing, SEO, social media, and AI automation - all
              included. Hands-on setup and ongoing support with every plan.
            </p>
          </div>
          <div className="lp-pricing-grid">
            {/* Free */}
            <div className="lp-pricing-card start-here reveal">
              <div className="lp-pricing-plan-name">Free</div>
              <div className="lp-pricing-tagline">
                See what AI can do for your business
              </div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$0</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">No credit card required</div>
              <div className="lp-pricing-divider"></div>
              <ul className="lp-pricing-features">
                <li>AI chat widget</li>
                <li>Customer capture</li>
                <li>Unlimited conversations</li>
                <li>Free forever</li>
                <li>Basic dashboard</li>
                <li>Email notifications</li>
                <li>Widget customization</li>
                <li>FAQ knowledge base</li>
                <li>Basic hosted business page</li>
                <li>Dashboard analytics</li>
                <li>Community support</li>
              </ul>
              <Link to="/signup" className="pricing-cta">
                Get Started {"\u2192"}
              </Link>
            </div>

            {/* Growth */}
            <div className="lp-pricing-card reveal">
              <div className="lp-pricing-plan-name">Growth</div>
              <div className="lp-pricing-tagline">Your AI front desk</div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$99</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">
                <span className="lp-pricing-waived-badge pulse-glow">
                  7-day free trial included
                </span>
              </div>
              <div className="lp-pricing-divider"></div>
              <ul className="lp-pricing-features">
                <li>AI chat widget</li>
                <li>Email &amp; form lead capture</li>
                <li>Auto follow-up email &amp; SMS</li>
                <li>Customer management</li>
                <li>Appointment booking</li>
                <li>2 automation sequences</li>
                <li>Up to 500 conversations/month</li>
                <li>Basic SEO audit &amp; recommendations</li>
                <li>AI content writer</li>
                <li>Hosted business page</li>
                <li>Basic analytics &amp; reporting</li>
                <li>Email support</li>
              </ul>
              <StripeCta plan="growth">Get Started {"\u2192"}</StripeCta>
            </div>

            {/* Professional - Most Popular */}
            <div className="lp-pricing-card popular reveal">
              <div className="lp-pricing-plan-name">Professional</div>
              <div className="lp-pricing-tagline">Automate your follow-ups</div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$150</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">
                No setup fee. Cancel anytime
              </div>
              <div className="lp-pricing-divider"></div>
              <div className="lp-pricing-includes">
                Everything in Growth, plus:
              </div>
              <ul className="lp-pricing-features">
                <li>Up to 6 automation sequences</li>
                <li>Lead nurturing sequences</li>
                <li>Pipeline automation</li>
                <li>AI-powered email responses</li>
                <li>Review request automation</li>
                <li>Full SEO audit suite &amp; keyword tracking</li>
                <li>Social media content &amp; scheduling</li>
                <li>Email &amp; SMS marketing campaigns</li>
                <li>AI marketing content generator</li>
                <li>Custom business page styling</li>
                <li>Advanced analytics &amp; insights</li>
                <li>Priority email &amp; chat support</li>
              </ul>
              <StripeCta plan="professional">Get Started {"\u2192"}</StripeCta>
            </div>

            {/* Enterprise */}
            <div className="lp-pricing-card reveal">
              <div className="lp-pricing-plan-name">Enterprise</div>
              <div className="lp-pricing-tagline">Your full AI employee</div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$250</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">
                No setup fee. Cancel anytime
              </div>
              <div className="lp-pricing-divider"></div>
              <div className="lp-pricing-includes">
                Everything in Professional, plus:
              </div>
              <ul className="lp-pricing-features">
                <li>Unlimited automation sequences</li>
                <li>AI appointment booking agent</li>
                <li>Team accounts &amp; roles</li>
                <li>AI visibility tracking (GEO score)</li>
                <li>Priority onboarding &amp; migration support</li>
                <li>Unlimited social media campaigns</li>
                <li>Webhook integrations</li>
                <li>White-label branding &amp; custom CSS</li>
                <li>White-glove business page design</li>
                <li>Full analytics suite</li>
                <li>Dedicated account manager</li>
              </ul>
              <StripeCta plan="enterprise">Get Started {"\u2192"}</StripeCta>
            </div>
          </div>
          <p className="lp-pricing-footer-note reveal">
            No setup fees. No contracts. All paid plans include hands-on
            onboarding and ongoing optimization. Cancel anytime.
          </p>
        </div>
      </section>

      {/* ============ FINAL CTA ============ */}
      <section className="lp-cta-section" id="cta">
        <div className="container lp-cta-content">
          <h2 className="section-title reveal">Ready to book more jobs?</h2>
          <div className="lp-cta-buttons reveal">
            <Link to="/signup" className="btn-primary">
              Get Started {"\u2192"}
            </Link>
            <Link to="/demo" className="btn-secondary">
              Book a Demo
            </Link>
          </div>
        </div>
      </section>

      {/* ============ DEMO PREVIEW ============ */}
      <DemoPreview />

      {/* ============ FAQ ============ */}
      <section className="section lp-faq" id="faq">
        <div className="container">
          <div className="lp-faq-header">
            <div className="section-label reveal">FAQ</div>
            <h2 className="section-title reveal">Frequently Asked Questions</h2>
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
                  ref={(el) => {
                    faqRefs.current[item.id] = el;
                  }}
                  style={{ maxHeight: getFaqMaxHeight(item.id) }}
                >
                  <div className="lp-faq-answer-inner">{item.answer}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
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
            {/* Social links removed until real profiles are created */}
          </div>
        </div>
      </footer>

      {/* ============ FLOATING CTA ============ */}
      {showFloatingCta && !floatingCtaDismissed && (
        <div className="lp-floating-cta">
          <Link to="/signup" className="lp-floating-cta-link">
            <span className="floating-cta-full">Try our AI assistant free</span>
            <span className="floating-cta-short">Try Out Our AI Assistant</span>
          </Link>
          <button
            className="lp-floating-cta-close"
            onClick={dismissFloatingCta}
            aria-label="Dismiss"
          >
            {"\u00D7"}
          </button>
        </div>
      )}
    </div>
  );
}
