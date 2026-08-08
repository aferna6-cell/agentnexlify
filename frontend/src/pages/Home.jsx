import { useState, useEffect, useCallback, useRef } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { trackEvent } from "../utils/analytics";
import { usePricingVariant } from "../utils/pricingExperiment";
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
function StripeCta({ plan, children, className }) {
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
    <a href="/signup" onClick={handleClick} className={className || "pricing-cta"}>
      {children}
    </a>
  );
}

const faqData = [
  {
    id: "faq-a1",
    question: "What's included in each plan?",
    answer:
      "Two plans. AI Front Desk is $19.99/month and includes the AI chat widget, lead capture, FAQ knowledge base, and appointment requests. AI Workforce is $99.99/month and adds the full platform: your AI marketing staff, SEO audit suite, social media scheduling, email and SMS campaigns, automation rules, and advanced analytics. No setup fees. Cancel anytime.",
  },
  {
    id: "faq-a2",
    question: "Do I need any technical skills?",
    answer:
      "None. You run your business by talking to your AI staff the way you would a real employee. The right department picks it up and shows you the work before anything goes out.",
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
      "Yes. Most businesses start with AI Front Desk and upgrade to AI Workforce as they grow. You can change your plan anytime from the Billing page.",
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
      "You stay in control. By default, every email, text, and invoice sits in your approvals queue until you review it. Nothing reaches a customer without your say-so.",
  },
  {
    id: "faq-a8",
    question: "How is this different from GoHighLevel or ChatGPT?",
    answer:
      "GoHighLevel takes real time to configure. ChatGPT is a general tool you have to build around yourself. AgentNexLiFy is done-for-you: describe what you need in plain language, an AI department picks it up, and you review the work before it goes out.",
  },
];

/* ── Demo slideshow tabs ── */
const demoTabs = [
  "AI Workforce",
  "Front Desk",
  "Leads",
  "Automations",
  "Calendar",
];

function DemoSlide({ tab }) {
  if (tab === "AI Workforce")
    return (
      <div className="ds-agent-os">
        <div className="ds-os-thread">
          <div className="ds-os-msg ds-os-msg-user">
            Follow up with the lead from yesterday who asked about a quote
          </div>
          <div className="ds-os-msg ds-os-msg-bot">
            <span className="ds-os-dept">Sales</span>
            Found Mike Chen from yesterday. He asked about kitchen remodel pricing.
            Here&apos;s a draft follow-up:
            <div className="ds-os-draft">
              &ldquo;Hi Mike, just checking in on the kitchen quote we discussed. Happy to answer any questions or schedule a walkthrough - just let me know.&rdquo;
            </div>
            <div className="ds-os-actions">
              <span className="ds-os-btn ds-os-btn-approve">Approve &amp; Send</span>
              <span className="ds-os-btn ds-os-btn-edit">Edit</span>
            </div>
          </div>
          <div className="ds-os-msg ds-os-msg-user">
            What&apos;s on my calendar this week?
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
            AI Front Desk - Online 24/7
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
        <div className="lp-demo-header reveal">
          <div className="section-label">See It In Action</div>
          <h2 className="section-title">Real product. Real workflows.</h2>
        </div>
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
          <Link to="/demo" className="lp-btn-primary">
            See it in action {"->"}
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  // Tracks the pricing A/B "view" event; variant no longer changes copy.
  usePricingVariant();
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
        <title>AgentNexLiFy | AI Workforce Platform for Small Business</title>
        <meta
          name="description"
          content="Agent NexLiFy builds AI workforces for small businesses. Start with an AI Front Desk, grow into a full AI Workforce run by a single AI manager."
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
  "description": "AI workforce platform for small businesses.",
  "url": "https://agentnexlify.com",
  "offers": [
    { "@type": "Offer", "name": "AI Front Desk", "price": "19.99", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "19.99", "priceCurrency": "USD", "billingDuration": "P1M" }
    },
    {
      "@type": "Offer", "name": "AI Workforce", "price": "99.99", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "99.99", "priceCurrency": "USD", "billingDuration": "P1M" }
    }
  ]
}
        `}</script>
        <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    { "@type": "Question", "name": "What's included in each plan?", "acceptedAnswer": { "@type": "Answer", "text": "Two plans. AI Front Desk is $19.99/month with the AI chat widget, lead capture, FAQ knowledge base, and appointment requests. AI Workforce is $99.99/month with the full platform: AI marketing staff, SEO audit suite, social media, campaigns, automation rules, and advanced analytics. No setup fees, cancel anytime." } },
    { "@type": "Question", "name": "Do I need any technical skills?", "acceptedAnswer": { "@type": "Answer", "text": "None. You run your business by talking to your AI staff the way you would a real employee. The right department picks it up and shows you the work before anything goes out." } },
    { "@type": "Question", "name": "What tools do you integrate with?", "acceptedAnswer": { "@type": "Answer", "text": "Google Calendar (built-in), plus outbound webhooks to connect with Zapier, Slack, HubSpot, and 5,000+ other tools. Twilio for SMS and Stripe for payments." } },
    { "@type": "Question", "name": "Can I upgrade my plan later?", "acceptedAnswer": { "@type": "Answer", "text": "Yes. Most businesses start with AI Front Desk and upgrade to AI Workforce as they grow. Change plans anytime from the Billing page." } },
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
            <a href="#compare" onClick={closeMenu}>
              Solutions
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
              <div className="lp-eyebrow reveal">AI WORKFORCE PLATFORM</div>
              <h1 className="reveal">
                Put Your Business On Autopilot With An AI Workforce
              </h1>
              <p className="lp-hero-sub reveal">
                Agent NexLiFy builds AI workforces for small businesses. Start
                with an AI Front Desk, grow into a full AI Workforce run by a
                single AI manager.
              </p>
              <div className="lp-hero-buttons reveal">
                <Link to="/signup" className="lp-btn-primary">
                  Get started
                </Link>
                <a href="#how-it-works" className="lp-btn-secondary">
                  See how it works
                </a>
              </div>
            </div>

            {/* Centerpiece org-chart diagram */}
            <div className="lp-org-diagram reveal">
              <div className="lp-org-owner">Business Owner</div>
              <div className="lp-org-connector-v" />
              <div className="lp-org-manager">AI Manager</div>
              <div className="lp-org-connector-v" />
              <div className="lp-org-agents">
                {[
                  "Sales",
                  "Marketing",
                  "Customer Support",
                  "Operations",
                  "Finance",
                  "HR",
                  "Knowledge",
                  "Executive Assistant",
                ].map((name) => (
                  <span key={name} className="lp-org-chip">{name}</span>
                ))}
              </div>
              <p className="lp-org-caption">
                One prompt controls the entire team.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ SPEED-TO-LEAD STATS ============ */}
      <section className="section lp-stats-band">
        <div className="container">
          <h2 className="lp-stats-headline reveal">
            Speed wins the customer. Every time.
          </h2>
          <div className="lp-stats-grid">
            <div className="lp-stat reveal">
              <div className="lp-stat-number">78%</div>
              <p className="lp-stat-text">
                of customers buy from the business that responds first
              </p>
            </div>
            <div className="lp-stat reveal">
              <div className="lp-stat-number">21&times;</div>
              <p className="lp-stat-text">
                more likely to qualify a lead when you reply within 5 minutes
                instead of 30
              </p>
            </div>
            <div className="lp-stat reveal">
              <div className="lp-stat-number">47 hrs</div>
              <p className="lp-stat-text">
                the average business takes nearly two days to answer a new lead
              </p>
            </div>
            <div className="lp-stat reveal">
              <div className="lp-stat-number">Seconds</div>
              <p className="lp-stat-text">
                how fast your AI front desk replies, nights and weekends
                included
              </p>
            </div>
          </div>
          <p className="lp-stats-source reveal">
            Sources: Harvard Business Review lead-response study (2.2M+ leads);
            InsideSales.com Lead Response Management research.
          </p>
        </div>
      </section>

      {/* ============ HOW IT WORKS ============ */}
      <section className="section lp-how-section" id="how-it-works">
        <div className="container">
          <div className="lp-how-header">
            <div className="section-label reveal">How It Works</div>
            <h2 className="section-title reveal">Three steps to an AI team.</h2>
          </div>
          <div className="lp-how-steps">
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">1</div>
              <h3>Tell your AI staff about your business</h3>
              <p>
                Answer a few questions about your services, prices, and how you
                work. The system builds a knowledge base from day one.
              </p>
            </div>
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">2</div>
              <h3>Add the widget to your website</h3>
              <p>
                One snippet of code. Your AI Front Desk answers visitors,
                captures leads, and books appointments 24/7.
              </p>
            </div>
            <div className="lp-how-step reveal">
              <div className="lp-how-step-num">3</div>
              <h3>Talk to your team, approve the work</h3>
              <p>
                Log in and describe what you need. The right department picks it
                up. You review and approve before anything goes out.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ AI FRONT DESK vs AI WORKFORCE ============ */}
      <section className="section lp-compare-section" id="compare">
        <div className="container">
          <div className="lp-compare-header">
            <div className="section-label reveal">Solutions</div>
            <h2 className="section-title reveal">
              Start with one. Grow into a team.
            </h2>
          </div>
          <div className="lp-compare-grid">
            <div className="lp-compare-card reveal">
              <div className="lp-compare-card-label">AI Front Desk</div>
              <p className="lp-compare-card-desc">
                Your website answers customers and captures leads around the
                clock.
              </p>
              <ul className="lp-compare-list">
                <li>Answers questions</li>
                <li>Captures leads</li>
                <li>Books appointments</li>
                <li>Supports customers</li>
              </ul>
              <div className="lp-compare-footer">Start here.</div>
            </div>
            <div className="lp-compare-card lp-compare-card-accent reveal">
              <div className="lp-compare-card-label">AI Workforce</div>
              <p className="lp-compare-card-desc">
                An AI office manager that runs the busywork for you, so you
                can run the business.
              </p>
              <ul className="lp-compare-list">
                <li>Follows up with every lead</li>
                <li>Runs your marketing &amp; social</li>
                <li>Answers customer questions</li>
                <li>Keeps your calendar booked</li>
                <li>Chases unpaid invoices</li>
                <li>Drafts quotes &amp; documents</li>
                <li>Handles routine admin</li>
                <li>You approve before anything sends</li>
              </ul>
              <div className="lp-compare-footer">Grow into it.</div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ DEMO PREVIEW ============ */}
      <DemoPreview />

      {/* ============ BUILT FOR YOUR BUSINESS ============ */}
      <section className="section lp-industries-section" id="industries">
        <div className="container">
          <div className="lp-industries-header">
            <div className="section-label reveal">Built For Your Business</div>
            <h2 className="section-title reveal">
              Works out of the box for your industry.
            </h2>
          </div>
          <div className="lp-industries-grid">
            <div className="lp-industry-card reveal">
              <div className="lp-industry-name">Salons &amp; Spas</div>
              <p>AI books appointments, sends reminders, and follows up on
              missed calls. Your front desk never goes offline.</p>
            </div>
            <div className="lp-industry-card reveal">
              <div className="lp-industry-name">Home Services</div>
              <p>Plumbers, HVAC, electricians. AI qualifies leads, schedules
              jobs, and sends estimates while you&apos;re on the truck.</p>
            </div>
            <div className="lp-industry-card reveal">
              <div className="lp-industry-name">Dental &amp; Medical</div>
              <p>Handles new patient inquiries, appointment requests, and FAQs
              so your staff focuses on care, not phones.</p>
            </div>
            <div className="lp-industry-card reveal">
              <div className="lp-industry-name">Contractors</div>
              <p>Captures every inquiry, drafts follow-up quotes, and tracks
              your pipeline. No lead slips through.</p>
            </div>
            <div className="lp-industry-card reveal">
              <div className="lp-industry-name">Auto Services</div>
              <p>AI answers service questions, books appointments, and sends
              service reminders to keep customers coming back.</p>
            </div>
            <div className="lp-industry-card reveal">
              <div className="lp-industry-name">Professional Services</div>
              <p>Law, accounting, consulting. AI qualifies prospects and
              schedules consultations so you close more business.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ PRICING ============ */}
      <section className="section lp-pricing-section" id="pricing">
        <div className="container">
          <div className="lp-pricing-header">
            <div className="section-label reveal">Pricing</div>
            <h2 className="section-title reveal">
              Simple pricing. No setup fees.
            </h2>
            <p className="section-subtitle reveal lp-pricing-sub">
              Both plans include hands-on onboarding. Cancel anytime.
            </p>
          </div>
          <div className="lp-pricing-grid">
            {/* AI Front Desk */}
            <div className="lp-pricing-card start-here reveal">
              <div className="lp-pricing-plan-name">AI Front Desk</div>
              <div className="lp-pricing-tagline">
                Handles your inbound traffic and the work behind it.
              </div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$19.99</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">No setup fee. Cancel anytime.</div>
              <div className="lp-pricing-usage">
                800K AI tokens/mo. Add more for $24.99/million.
              </div>
              <div className="lp-pricing-divider"></div>
              <ul className="lp-pricing-features">
                <li>AI chat widget that answers questions 24/7</li>
                <li>Lead capture with instant notifications</li>
                <li>Appointment requests through the widget</li>
                <li>FAQ knowledge base trained on your business</li>
                <li>Widget customization</li>
                <li>Hosted business page</li>
              </ul>
              <StripeCta plan="chatbot" className="lp-pricing-cta">Get Started {"->"}
              </StripeCta>
            </div>

            {/* AI Workforce */}
            <div className="lp-pricing-card popular reveal">
              <div className="lp-pricing-plan-name">AI Workforce</div>
              <div className="lp-pricing-tagline">
                An AI office manager that runs the busywork for you.
              </div>
              <div className="lp-pricing-amount">
                <span className="lp-pricing-dollar">$99.99</span>
                <span className="lp-pricing-period">/month</span>
              </div>
              <div className="lp-pricing-setup">
                No setup fee. Cancel anytime.
              </div>
              <div className="lp-pricing-usage">
                5M AI tokens/mo. Add more for $24.99/million.
              </div>
              <div className="lp-pricing-divider"></div>
              <div className="lp-pricing-includes">
                Everything in AI Front Desk, plus:
              </div>
              <ul className="lp-pricing-features">
                <li>Full AI Workforce: sales, marketing, operations, finance, HR</li>
                <li>Full SEO audit suite &amp; keyword tracking</li>
                <li>Social media content &amp; scheduling</li>
                <li>Email &amp; SMS marketing campaigns</li>
                <li>Automation rules &amp; advanced analytics</li>
                <li>Priority support</li>
              </ul>
              <StripeCta plan="agent_os" className="lp-pricing-cta lp-pricing-cta-accent">
                Get Started {"->"}
              </StripeCta>
            </div>
          </div>
          <p className="lp-pricing-footer-note reveal">
            No setup fees. Cancel anytime.
          </p>
        </div>
      </section>

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

      {/* ============ FINAL CTA ============ */}
      <section className="lp-cta-section" id="cta">
        <div className="container lp-cta-content">
          <h2 className="lp-cta-title reveal">
            Your AI staff is ready to start today.
          </h2>
          <p className="lp-cta-sub reveal">
            No setup fees. Cancel anytime. Takes 2 minutes.
          </p>
          <div className="lp-cta-buttons reveal">
            <Link to="/signup" className="lp-btn-primary">
              Get Started {"->"}
            </Link>
            <Link to="/demo" className="lp-btn-secondary">
              See it in action
            </Link>
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
                  <a href="#compare">Solutions</a>
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
                  <Link to="/demo">Live Demo</Link>
                </li>
              </ul>
            </div>
            <div className="lp-footer-col">
              <h4>Industries</h4>
              <ul>
                <li>
                  <Link to="/ai-front-desk/salons">Salons &amp; Spas</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/plumbers">Plumbing &amp; HVAC</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/dentists">Dental Offices</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/med-spas">Med Spas</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/auto-repair">Auto Repair</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/real-estate">Real Estate</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/law-firms">Law Firms</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/restaurants">Restaurants</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/fitness">Fitness Studios</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/roofing">Roofing</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/cleaning-services">Cleaning Services</Link>
                </li>
                <li>
                  <Link to="/ai-front-desk/veterinary">Veterinary Clinics</Link>
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

      {/* ============ FLOATING CTA ============ */}
      {showFloatingCta && !floatingCtaDismissed && (
        <div className="lp-floating-cta">
          <Link to="/signup" className="lp-floating-cta-link">
            <span className="floating-cta-full">Get your AI staff started</span>
            <span className="floating-cta-short">Try Our AI Staff</span>
          </Link>
          <button
            className="lp-floating-cta-close"
            onClick={dismissFloatingCta}
            aria-label="Dismiss"
          >
            {"x"}
          </button>
        </div>
      )}
    </div>
  );
}
