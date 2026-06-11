import { useState, useEffect, useCallback, useRef } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { trackEvent } from "../utils/analytics";
import { usePricingVariant, trackPricingEvent } from "../utils/pricingExperiment";
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
    question: "What’s included in each plan?",
    answer:
      "Every plan builds on the previous tier. Free includes the chat widget, customer capture, and FAQ knowledge base. Growth is $99/month and includes a 7-day free trial, appointment booking, SMS, auto follow-up, and the AI content writer. Professional is $150/month and adds the full SEO suite, social media scheduling, email and SMS campaigns, and advanced analytics. Enterprise is $250/month and adds AI visibility tracking, competitor analysis, team accounts, webhooks, and white-label branding.",
  },
  {
    id: "faq-a2",
    question: "Do I need any technical skills?",
    answer:
      "None. You run your business by talking to your AI staff the way you would a real employee: “follow up with the lead from yesterday,” “draft an invoice for the Hendersons.” The right department picks it up and shows you the work before anything goes out.",
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
      "Yes. Start free or on Growth and upgrade as your business grows. You can change your plan anytime from the Billing page.",
  },
  {
    id: "faq-a6",
    question: "Is there a contract?",
    answer: "No long-term contracts. Month-to-month billing. Cancel anytime.",
  },
  {
    id: "faq-a7",
    question: "What if the AI makes a mistake?",
    answer:
      "You stay in control. By default, every email, text, and invoice sits in your approvals queue until you review it. Nothing reaches a customer without your say-so. If you trust a department to handle routine items on its own, you can turn on auto-send in Settings and turn it off any time.",
  },
  {
    id: "faq-a8",
    question: "How is this different from GoHighLevel or ChatGPT?",
    answer:
      "GoHighLevel is a deep CRM that takes real time to configure. ChatGPT is a general tool you have to build around yourself. AgentNexLiFy is done-for-you: you describe what you need in plain language, an AI department picks it up, and you review the work before it goes out. No pipelines to build, no prompts to write.",
  },
];

/* ── Demo slideshow tabs ── */
const demoTabs = [
  "Agent OS",
  "Front Desk",
  "Leads",
  "Automations",
  "Calendar",
];

function DemoSlide({ tab }) {
  if (tab === "Agent OS")
    return (
      <div className="ds-agent-os">
        <div className="ds-os-thread">
          <div className="ds-os-msg ds-os-msg-user">
            Follow up with the lead from yesterday who asked about a quote
          </div>
          <div className="ds-os-msg ds-os-msg-bot">
            <span className="ds-os-dept">Sales</span>
            Found Mike Chen from yesterday. He asked about kitchen remodel pricing.
            Here’s a draft follow-up:
            <div className="ds-os-draft">
              &ldquo;Hi Mike, just checking in on the kitchen quote we discussed. Happy to answer any questions or schedule a walkthrough—just let me know.&rdquo;
            </div>
            <div className="ds-os-actions">
              <span className="ds-os-btn ds-os-btn-approve">Approve &amp; Send</span>
              <span className="ds-os-btn ds-os-btn-edit">Edit</span>
            </div>
          </div>
          <div className="ds-os-msg ds-os-msg-user">
            What’s on my calendar this week?
          </div>
          <div className="ds-os-msg ds-os-msg-bot">
            <span className="ds-os-dept">Operations</span>
            3 appointments this week: Mon 9 AM Sarah J., Wed 11 AM James W., Thu 2 PM new consult. 2 invoices outstanding totaling $4,200.
          </div>
        </div>
      </div>
    );

  if (tab === "Front Desk")
    return (
      <div className="ds-chat">
        <div className="ds-chat-window">
          <div className="ds-chat-header">
            <span className="ds-chat-status" />
            AI Front Desk &mdash; Online 24/7
          </div>
          <div className="ds-chat-body">
            <div className="ds-msg bot">Hi! How can I help you today?</div>
            <div className="ds-msg user">
              I&apos;d like to schedule a consultation
            </div>
            <div className="ds-msg bot">
              Of course! What day works best for you?
            </div>
            <div className="ds-msg user">How about Thursday at 2pm?</div>
            <div className="ds-msg bot">
              Thursday at 2:00 PM is available. Booked! You&apos;ll get a
              confirmation shortly.
            </div>
          </div>
          <div className="ds-chat-input">
            <span>Type a message...</span>
          </div>
        </div>
      </div>
    );

  if (tab === "Leads")
    return (
      <div className="ds-clients">
        <div className="ds-panel-title">Leads &amp; Customers</div>
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
        <div className="ds-panel-title">Follow-Up Sequence: New Lead</div>
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
          <h2 className="section-title">See It In Action</h2>
          <Link to="/demo" className="btn-primary">
            Book a Demo {"→"}
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const pricingVariant = usePricingVariant();
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
        <title>AgentNexLiFy &mdash; AI Staff for Small Businesses</title>
        <meta
          name="description"
          content="AgentNexLiFy gives your small business an AI staff that handles sales follow-ups, booking, invoicing, and marketing from one chat. Your website widget captures customers 24/7. Start free."
        />
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
  "description": "AI staff for small businesses. Handles follow-ups, bookings, invoicing, and marketing from one chat. Website widget captures customers 24/7.",
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
  "description": "AI-powered business operating system for small businesses.",
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
    { "@type": "Question", "name": "What's included in each plan?", "acceptedAnswer": { "@type": "Answer", "text": "Free includes the chat widget, customer capture, and FAQ knowledge base. Growth is $99/month with a 7-day free trial, booking, SMS, auto follow-up, and the AI content writer. Professional is $150/month with SEO suite, social media, campaigns, and advanced analytics. Enterprise is $250/month with AI visibility tracking, competitor analysis, team accounts, webhooks, and white-label branding." } },
    { "@type": "Question", "name": "Do I need any technical skills?", "acceptedAnswer": { "@type": "Answer", "text": "None. You run your business by talking to your AI staff the way you would a real employee. The right department picks it up and shows you the work before anything goes out." } },
    { "@type": "Question", "name": "What tools do you integrate with?", "acceptedAnswer": { "@type": "Answer", "text": "Google Calendar (built-in), plus outbound webhooks to connect with Zapier, Slack, HubSpot, and 5,000+ other tools. Twilio for SMS and Stripe for payments." } },
    { "@type": "Question", "name": "Can I upgrade my plan later?", "acceptedAnswer": { "@type": "Answer", "text": "Yes. Start free or on Growth and upgrade as your business grows. Change plans anytime from the Billing page." } },
    { "@type": "Question", "name": "Is there a contract?", "acceptedAnswer": { "@type": "Answer", "text": "No long-term contracts. Month-to-month billing. Cancel anytime." } },
    { "@type": "Question", "name": "What if the AI makes a mistake?", "acceptedAnswer": { "@type": "Answer", "text": "You stay in control. Every email, text, and invoice sits in your approvals queue until you review it. Nothing reaches a customer without your say-so." } },
    { "@type": "Question", "name": "How is this different from GoHighLevel or ChatGPT?", "acceptedAnswer": { "@type": "Answer", "text": "GoHighLevel takes real time to configure. ChatGPT is a general tool you have to build around yourself. AgentNexLiFy is done-for-you: describe what you need in plain language, an AI department picks it up, and you review the work before it goes out." } }
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
              <div className="lp-hero-badge reveal">
                <span className="lp-hero-badge-dot" />
                AI staff, not another tool to learn
              </div>
              <h1 className="reveal">
                Run your business by{" "}
                <span className="accent-gradient">talking to your AI staff.</span>
              </h1>
              <p
                className="lp-hero-sub reveal"
              >
                Eight AI departments handle follow-ups, bookings, invoices, and
                marketing. Your 24/7 website widget captures customers while you
                sleep. You approve everything from one chat.
              </p>
              <div className="lp-hero-buttons reveal">
                <Link to="/signup" className="btn-primary">
                  Start free {"→"}
                </Link>
                <a href="#how-it-works" className="btn-secondary">
                  See how it works
                </a>
              </div>
            </div>

            {/* Agent OS chat mockup */}
            <div className="widget-mockup reveal">
              <div className="widget-mockup-header">
                <div className="widget-mockup-avatar">AI</div>
                <div className="widget-mockup-header-text">
                  <div className="widget-mockup-name">Agent OS</div>
                  <div className="widget-mockup-status">
                    <span className="widget-mockup-status-dot"></span>
                    8 departments ready
                  </div>
                </div>
              </div>
              <div className="widget-mockup-body">
                <div className="wm-msg wm-msg-user">
                  Follow up with yesterday&apos;s leads who asked for a quote
                </div>
                <div className="wm-typing" aria-hidden="true">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <div className="wm-msg wm-msg-bot">
                  Found 3 leads. Drafting follow-ups now&mdash;I&apos;ll show
                  you each one before anything sends.
                </div>
                <div className="wm-msg wm-msg-user">
                  Also send an invoice to the Hendersons for the job we finished
                </div>
                <div className="wm-msg wm-msg-bot">
                  Invoice drafted for $1,840. Ready for your review.
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
              One chat. Your whole business.
            </h2>
          </div>
          <div className="lp-how-steps">
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">1</div>
              <h3>Tell your AI staff about your business</h3>
              <p>
                Answer a few questions about your services, prices, and how you
                work. The system builds a knowledge base so every department
                knows your business from day one.
              </p>
            </div>
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">2</div>
              <h3>Add the widget to your website</h3>
              <p>
                One small piece of code goes on your site. Your 24/7 AI front
                desk answers visitors, captures their details, and books
                appointments&mdash;even at 11 PM.
              </p>
            </div>
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">3</div>
              <h3>Talk to your team, approve the work</h3>
              <p>
                Log in and describe what you need: &ldquo;follow up with this
                week&apos;s leads,&rdquo; &ldquo;draft an invoice.&rdquo; The
                right department picks it up. You review and approve before
                anything goes out.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ FEATURES / DEPARTMENTS ============ */}
      <section
        className="section"
        id="features"
        style={{ background: "var(--bg-secondary)" }}
      >
        <div className="container">
          <div className="lp-features-header">
            <div className="section-label reveal">Departments</div>
            <h2 className="section-title reveal">
              Eight departments. One conversation.
            </h2>
            <p className="section-subtitle reveal" style={{ margin: "0 auto" }}>
              Every part of running a small business, handled by AI staff that
              knows your business and waits for your approval before acting.
            </p>
          </div>
          <div className="lp-features-grid">
            {/* Front Desk */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <h3>Front Desk Widget</h3>
              <p>
                Answers customer questions on your website 24/7, captures
                contact details, and books appointments on the spot. Every
                conversation feeds your AI staff automatically.
              </p>
            </div>
            {/* Sales */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
              </div>
              <h3>Sales Follow-Up</h3>
              <p>
                Drafts follow-up emails and texts for every lead, times them
                correctly, and moves prospects toward booked work. You approve
                before anything sends.
              </p>
            </div>
            {/* Operations */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
              </div>
              <h3>Operations</h3>
              <p>
                Keeps scheduling, appointments, and day-to-day tasks moving.
                Ask what&apos;s on your calendar this week and get a plain-English
                answer in seconds.
              </p>
            </div>
            {/* Invoicing */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="1" x2="12" y2="23" />
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
              </div>
              <h3>Invoicing</h3>
              <p>
                Drafts invoices, sends payment reminders, and chases overdue
                balances. Say &ldquo;send an invoice to the Hendersons&rdquo; and it
                handles the rest.
              </p>
            </div>
            {/* Marketing */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                </svg>
              </div>
              <h3>Marketing</h3>
              <p>
                Writes campaigns, social posts, and promotions in your voice.
                Schedule posts across platforms without leaving your dashboard.
              </p>
            </div>
            {/* Memory */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <ellipse cx="12" cy="5" rx="9" ry="3" />
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                </svg>
              </div>
              <h3>Business Memory</h3>
              <p>
                Learns your customers, prices, preferences, and how you like
                things done. Less repeating yourself over time. Every fact is
                visible and editable in the Memory panel.
              </p>
            </div>
            {/* Customer Data */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </div>
              <h3>Customer Records</h3>
              <p>
                All your leads and customers in one place, scored and organized
                so you know who to focus on. Pipeline view shows every deal and
                where it stands.
              </p>
            </div>
            {/* Approval Control */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 11 12 14 22 4" />
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                </svg>
              </div>
              <h3>Approval Control</h3>
              <p>
                Nothing reaches a customer until you approve it. Review every
                email, text, and invoice in your queue. Turn on auto-send for
                routine items when you&apos;re ready to.
              </p>
            </div>
            {/* SEO & Online Presence */}
            <div className="lp-feature-card reveal">
              <div className="lp-feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <h3>SEO and Online Presence</h3>
              <p>
                Audits your website, tracks your keyword rankings, and gives
                you clear steps to show up higher in search. Includes a hosted
                business page if you need one.
              </p>
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
              AI staff from $0. No setup fees.
            </h2>
            <p className="section-subtitle reveal">
              Start free and add departments as your business grows. Every paid
              plan includes hands-on onboarding and ongoing optimization.
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
              <Link
                to="/signup"
                className="pricing-cta"
                onClick={() => trackPricingEvent("cta_click", "free")}
              >
                {pricingVariant === "variant_b"
                  ? "Try It Free — 2-Minute Setup →"
                  : "Get Started →"}
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
              <StripeCta plan="growth">Get Started {"→"}</StripeCta>
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
              <StripeCta plan="professional">Get Started {"→"}</StripeCta>
            </div>

            {/* Enterprise */}
            <div className="lp-pricing-card reveal">
              <div className="lp-pricing-plan-name">Enterprise</div>
              <div className="lp-pricing-tagline">Your full AI staff</div>
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
              <StripeCta plan="enterprise">Get Started {"→"}</StripeCta>
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
          <h2 className="section-title reveal">
            Your AI staff is ready to start today.
          </h2>
          <p className="section-subtitle reveal" style={{ margin: "0 auto 32px", textAlign: "center" }}>
            Free to start. No credit card. Takes 2 minutes to set up.
          </p>
          <div className="lp-cta-buttons reveal">
            <Link to="/signup" className="btn-primary">
              Get Started Free {"→"}
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
              <p>AI staff for small businesses. One chat handles everything.</p>
            </div>
            <div className="lp-footer-col">
              <h4>Product</h4>
              <ul>
                <li>
                  <a href="#how-it-works">How It Works</a>
                </li>
                <li>
                  <a href="#features">Departments</a>
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
                  <Link to="/help">Help Center</Link>
                </li>
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
            <span className="floating-cta-full">Start with AI staff free</span>
            <span className="floating-cta-short">Try Out Our AI Staff</span>
          </Link>
          <button
            className="lp-floating-cta-close"
            onClick={dismissFloatingCta}
            aria-label="Dismiss"
          >
            {"×"}
          </button>
        </div>
      )}
    </div>
  );
}
