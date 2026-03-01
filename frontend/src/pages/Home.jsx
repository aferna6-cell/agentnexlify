import React, { useState, useEffect, useCallback, useRef } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import "../styles/home.css";

const CALENDLY_URL = "https://calendly.com/aidanfernandes31/15-minute-agent-nexliffy-demo";

const faqData = [
  {
    id: "faq-a1",
    question: "What\u2019s included in each plan?",
    answer:
      "Every plan builds on the one below it. Foundation ($99) covers lead capture, review requests, missed call texts, and appointment reminders. Growth ($249) adds follow-up sequences, FAQ bot, quote automation, and CRM. Operations ($499) adds AI booking, invoice follow-up, task automation, and lead scoring. Enterprise ($999) is the full package with AI sales assistant, marketing engine, dashboard, and re-engagement campaigns.",
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
      "Most businesses we work with are fully live within 48 hours of our kickoff call. Complex custom workflows may take up to a week.",
  },
  {
    id: "faq-a5",
    question: "Can I upgrade my plan later?",
    answer:
      "Absolutely. Most of our partners start with Foundation or Growth and upgrade within a few months once they see results. We\u2019ll migrate everything seamlessly with no downtime and no lost data.",
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
      "Our automations are designed with human-in-the-loop checkpoints. For emails, you review and approve before sending. For lead capture, the AI qualifies and you close. You stay in control.",
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

  // Nav scroll detection
  useEffect(() => {
    const handleScroll = () => {
      setNavScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Lock body scroll when mobile menu open
  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  // Reveal animations with IntersectionObserver
  useEffect(() => {
    const reveals = document.querySelectorAll(".reveal");
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

  const toggleMenu = useCallback(() => {
    setMenuOpen((prev) => !prev);
  }, []);

  const closeMenu = useCallback(() => {
    setMenuOpen(false);
  }, []);

  const handleFaqToggle = useCallback((id) => {
    setOpenFaq((prev) => (prev === id ? null : id));
  }, []);

  // Compute max-height for open FAQ answer
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
    <>
      <Helmet>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>AgentNexLiFy | Free AI Chatbot for Local Businesses</title>
        <meta
          name="description"
          content="Add a free AI chatbot to your local business website. Handle inquiries 24/7, capture leads, and automate bookings — no coding required."
        />
        <link rel="canonical" href="https://agentnexlify.com/" />
        <meta property="og:title" content="AgentNexLiFy | Free AI Chatbot for Local Businesses" />
        <meta
          property="og:description"
          content="Add a free AI chatbot to your local business website. Handle inquiries 24/7, capture leads, and automate bookings — no coding required."
        />
        <meta property="og:image" content="https://agentnexlify.com/og-image.png" />
        <meta property="og:url" content="https://agentnexlify.com/" />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="AgentNexLiFy | Free AI Chatbot for Local Businesses" />
        <meta
          name="twitter:description"
          content="Add a free AI chatbot to your local business website. Handle inquiries 24/7, capture leads, and automate bookings — no coding required."
        />
        <meta name="twitter:image" content="https://agentnexlify.com/og-image.png" />
        <meta name="google-site-verification" content="87NEEvBU6dL3QuI_1iZK9wgq4Jtws60z1M3bKu-mS6s" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Outfit:wght@400;500;600;700;800&display=swap"
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
  },
  "sameAs": ["FILL_IN_LINKEDIN", "FILL_IN_TWITTER"]
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
    {
      "@type": "Offer",
      "name": "Free",
      "price": "0",
      "priceCurrency": "USD",
      "description": "Free AI chatbot widget for your website"
    },
    {
      "@type": "Offer",
      "name": "Foundation",
      "price": "99",
      "priceCurrency": "USD",
      "priceSpecification": {
        "@type": "UnitPriceSpecification",
        "price": "99",
        "priceCurrency": "USD",
        "billingDuration": "P1M"
      },
      "description": "Lead capture, review requests, missed call texts, and appointment reminders"
    },
    {
      "@type": "Offer",
      "name": "Growth",
      "price": "249",
      "priceCurrency": "USD",
      "priceSpecification": {
        "@type": "UnitPriceSpecification",
        "price": "249",
        "priceCurrency": "USD",
        "billingDuration": "P1M"
      },
      "description": "Follow-up sequences, FAQ bot, quote automation, and CRM"
    },
    {
      "@type": "Offer",
      "name": "Operations",
      "price": "499",
      "priceCurrency": "USD",
      "priceSpecification": {
        "@type": "UnitPriceSpecification",
        "price": "499",
        "priceCurrency": "USD",
        "billingDuration": "P1M"
      },
      "description": "AI booking, invoice follow-up, task automation, and lead scoring"
    }
  ]
}
        `}</script>
        <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What's included in each plan?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Every plan builds on the one below it. Foundation ($99) covers lead capture, review requests, missed call texts, and appointment reminders. Growth ($249) adds follow-up sequences, FAQ bot, quote automation, and CRM. Operations ($499) adds AI booking, invoice follow-up, task automation, and lead scoring. Enterprise ($999) is the full package with AI sales assistant, marketing engine, dashboard, and re-engagement campaigns."
      }
    },
    {
      "@type": "Question",
      "name": "Do I need any technical skills?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Not at all. We handle 100% of the setup, integration, and ongoing management. If you can use email, you can use Agent NexLiFy."
      }
    },
    {
      "@type": "Question",
      "name": "What tools do you integrate with?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Gmail, Outlook, Google Calendar, Calendly, most CRMs (HubSpot, Follow Up Boss, Salesforce), Slack, QuickBooks, and more. If you use it, we can probably connect to it."
      }
    },
    {
      "@type": "Question",
      "name": "How long does setup take?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Most businesses we work with are fully live within 48 hours of our kickoff call. Complex custom workflows may take up to a week."
      }
    },
    {
      "@type": "Question",
      "name": "Can I upgrade my plan later?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Absolutely. Most of our partners start with Foundation or Growth and upgrade within a few months once they see results. We'll migrate everything seamlessly with no downtime and no lost data."
      }
    },
    {
      "@type": "Question",
      "name": "Is there a contract?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No long-term contracts. Month-to-month billing. Cancel anytime."
      }
    },
    {
      "@type": "Question",
      "name": "What if AI makes a mistake?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Our automations are designed with human-in-the-loop checkpoints. For emails, you review and approve before sending. For lead capture, the AI qualifies and you close. You stay in control."
      }
    },
    {
      "@type": "Question",
      "name": "How is this different from Zapier or ChatGPT?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Those are tools. You still have to build, manage, and fix everything yourself. Agent NexLiFy is a service. We do the work. You get the results."
      }
    }
  ]
}
        `}</script>
      </Helmet>

      {/* ============ NAV ============ */}
      <nav className={`nav${navScrolled ? " scrolled" : ""}`} role="navigation" aria-label="Main navigation">
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
              <a href="#why" onClick={closeMenu}>
                Why Us
              </a>
            </li>
            <li>
              <a href="#features" onClick={closeMenu}>
                Features
              </a>
            </li>
            <li>
              <a href="#how-it-works" onClick={closeMenu}>
                How It Works
              </a>
            </li>
            <li>
              <a href="#pricing" onClick={closeMenu}>
                Pricing
              </a>
            </li>
            <li>
              <a href="#about-us" onClick={closeMenu}>
                About
              </a>
            </li>
            <li>
              <Link to="/free-widget" onClick={closeMenu}>
                Free AI Widget
              </Link>
            </li>
            <li>
              <button className="nav-search" aria-label="Search">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </button>
            </li>
          </ul>
          <a href="#" className="nav-logo">
            <img src="/logo.png" alt="Agent NexLiFy" />
          </a>
          <div className="nav-right">
            <button className="nav-lang" aria-label="Language">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
              <span>EN</span>
            </button>
            <a href={CALENDLY_URL} className="nav-login">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <span>Login</span>
            </a>
            <a href={CALENDLY_URL} className="nav-cta">
              Book a Strategy Call
            </a>
          </div>
        </div>
      </nav>

      {/* ============ HERO ============ */}
      <section className="hero">
        <div className="container hero-content">
          <img src="/logo.png" alt="Agent NexLiFy Logo" className="hero-logo reveal" />
          <div className="hero-badge reveal">
            <span className="hero-badge-dot" aria-hidden="true"></span>
            Built to give business owners their time back
          </div>
          <h1 className="reveal">
            Focus on what you do best.
            <br />
            <span className="accent">We&#39;ll handle the rest.</span>
          </h1>
          <p className="hero-sub reveal">
            Agent NexLiFy builds practical automation systems that manage your leads, customer interactions, internal
            workflows, and administrative tasks so you can spend less time managing and more time growing.
          </p>
          <div className="hero-buttons reveal">
            <a href={CALENDLY_URL} className="btn-primary">
              Book a Strategy Call {"\u2192"}
            </a>
            <a href="#how-it-works" className="btn-secondary">
              See How It Works {"\u2193"}
            </a>
          </div>
          <div className="trust-bar reveal">
            <p className="trust-bar-label">Trusted by businesses using</p>
            <div className="trust-bar-logos">
              {/* Gmail */}
              <svg viewBox="0 0 24 24" aria-label="Gmail">
                <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z" />
              </svg>
              {/* Google Calendar */}
              <svg viewBox="0 0 24 24" aria-label="Google Calendar">
                <path d="M18.316 5.684H24v12.632h-5.684V5.684zM5.684 24h12.632v-5.684H5.684V24zM18.316 5.684V0H5.684v5.684h12.632zM5.684 18.316H0V5.684h5.684v12.632zM7.953 14.39l1.478-1.149c.543.49 1.142.735 1.797.735.654 0 1.108-.254 1.108-.815 0-.462-.336-.735-1.01-.998l-.736-.287c-1.087-.42-1.621-1.109-1.621-2.098 0-1.314 1.034-2.197 2.507-2.197.922 0 1.72.342 2.274.943l-1.264 1.155c-.385-.336-.77-.504-1.176-.504-.44 0-.748.222-.748.598 0 .368.253.586.849.81l.748.288c1.216.468 1.785 1.108 1.785 2.24 0 1.351-1.064 2.344-2.67 2.344-1.143 0-2.07-.434-2.72-1.264l.4-.8z" />
              </svg>
              {/* HubSpot */}
              <svg viewBox="0 0 24 24" aria-label="HubSpot">
                <path d="M18.164 7.93V5.084a2.198 2.198 0 0 0 1.267-1.984v-.066a2.2 2.2 0 0 0-2.198-2.198h-.066a2.2 2.2 0 0 0-2.198 2.198v.066c0 .865.506 1.61 1.233 1.966v2.862a5.662 5.662 0 0 0-2.905 1.384l-7.666-5.97a2.39 2.39 0 0 0 .072-.563 2.413 2.413 0 1 0-2.413 2.413c.437 0 .842-.122 1.2-.325l7.544 5.876a5.668 5.668 0 0 0-.478 2.279 5.681 5.681 0 0 0 .565 2.47l-2.262 2.263a1.88 1.88 0 0 0-.573-.097 1.902 1.902 0 1 0 1.901 1.901c0-.2-.035-.39-.092-.572l2.235-2.235a5.686 5.686 0 0 0 3.45 1.17h.002a5.69 5.69 0 1 0 0-11.38 5.69 5.69 0 0 0-2.576.612l-.062.033zm.062 8.151h-.002a2.843 2.843 0 1 1 .002 0z" />
              </svg>
              {/* Salesforce */}
              <svg viewBox="0 0 24 24" aria-label="Salesforce">
                <path d="M10.006 5.415a4.195 4.195 0 0 1 3.045-1.306c1.56 0 2.954.9 3.69 2.205a4.89 4.89 0 0 1 2.013-.432c2.735 0 4.952 2.23 4.952 4.98s-2.217 4.98-4.952 4.98a4.937 4.937 0 0 1-.765-.06 3.469 3.469 0 0 1-3.089 1.913 3.469 3.469 0 0 1-1.48-.332 4.14 4.14 0 0 1-3.783 2.47 4.14 4.14 0 0 1-3.682-2.25 3.596 3.596 0 0 1-.61.053c-1.987 0-3.598-1.62-3.598-3.618a3.61 3.61 0 0 1 1.487-2.918A4.39 4.39 0 0 1 3 9.09c0-2.442 1.976-4.42 4.414-4.42 1.466 0 2.632.604 3.592 1.745z" />
              </svg>
              {/* Slack */}
              <svg viewBox="0 0 24 24" aria-label="Slack">
                <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.122 2.521a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.268 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zm-2.523 10.122a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.268a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
              </svg>
              {/* QuickBooks */}
              <svg viewBox="0 0 24 24" aria-label="QuickBooks">
                <path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zm5.723 16.17h-1.807c0 1.268-1.027 2.297-2.294 2.297v-1.81c0-2.049-.006-4.098.003-6.147.003-.596-.003-1.057-.699-1.286-.938-.31-1.89.37-1.89 1.382.004 2.037.001 4.074.002 6.11v1.75h-1.81c0 1.268-1.026 2.297-2.293 2.297V7.833h1.81c0-1.27 1.026-2.297 2.293-2.297v1.81c0 2.048.006 4.097-.003 6.146-.003.596.003 1.058.699 1.287.938.309 1.89-.371 1.89-1.383-.004-2.037-.001-4.074-.002-6.11v-1.75h1.808c0-1.27 1.026-2.298 2.293-2.298V16.17z" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* ============ WHY AGENT NEXLIFY ============ */}
      <section className="section why" id="why">
        <div className="container why-inner">
          <div className="section-label reveal">Why Agent NexLiFy</div>
          <h2 className="section-title reveal">You started your business for a reason. Let&#39;s get you back to it.</h2>
          <p className="why-body reveal">
            Emails. Leads. Scheduling. Follow-ups. Admin. The daily grind quietly takes over your calendar. Before long,
            you&#39;re spending more time managing tasks than driving growth. You didn&#39;t build your business to manage
            busywork.
          </p>
          <p className="why-body reveal">
            What if your leads were captured automatically? What if follow-ups went out on time, every time? What if
            scheduling didn&#39;t require endless back-and-forth? When systems handle the repetitive work, you get your time
            back.
          </p>
          <blockquote className="why-quote reveal">
            {"\u201C"}We&#39;re not here to sell you software. We&#39;re here to help you grow.{"\u201D"}
          </blockquote>
        </div>
      </section>

      {/* ============ WHAT WE AUTOMATE ============ */}
      <section className="section" id="features">
        <div className="container">
          <div className="features-header">
            <div className="section-label reveal">What We Automate</div>
            <h2 className="section-title reveal">Practical automation built for real businesses.</h2>
            <p className="section-subtitle reveal">
              We design, implement, and manage AI-powered workflows tailored to your operations. No complex software to
              learn. No technical setup on your end. We handle everything so your systems run smoothly behind the scenes.
            </p>
          </div>
          <div className="features-grid">
            <div className="feature-card reveal">
              <div className="feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <h3>Lead Capture &amp; Qualification</h3>
              <p>AI chatbot captures, qualifies, and routes leads 24/7 so you never miss an opportunity.</p>
            </div>
            <div className="feature-card reveal">
              <div className="feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
              </div>
              <h3>Follow-Up Sequences</h3>
              <p>Automated email + SMS drip campaigns that nurture every lead with AI-personalized messaging.</p>
            </div>
            <div className="feature-card reveal">
              <div className="feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
              </div>
              <h3>Reviews &amp; Reputation</h3>
              <p>Automatic review requests after every job. More 5-star reviews on autopilot.</p>
            </div>
            <div className="feature-card reveal">
              <div className="feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              </div>
              <h3>Scheduling &amp; Reminders</h3>
              <p>AI books appointments, sends reminders, handles reschedules. No more no-shows.</p>
            </div>
            <div className="feature-card reveal">
              <div className="feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              </div>
              <h3>CRM &amp; Pipeline</h3>
              <p>Auto-tag leads, move deal stages, trigger alerts. Your pipeline manages itself.</p>
            </div>
            <div className="feature-card reveal">
              <div className="feature-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a4 4 0 0 1 4 4c0 1.95-1.4 3.58-3.25 3.93"/><path d="M8.24 9.93A4 4 0 0 1 12 2"/><path d="M12 18v4"/><path d="M8 22h8"/><rect x="7" y="10" width="10" height="8" rx="1"/></svg>
              </div>
              <h3>AI Sales &amp; Support</h3>
              <p>
                AI handles FAQs, generates quotes, and responds to inquiries like a team member that never sleeps.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ HOW IT WORKS ============ */}
      <section className="section how" id="how-it-works">
        <div className="container">
          <div className="how-header">
            <div className="section-label reveal">How It Works</div>
            <h2 className="section-title reveal">Simple setup. We do the heavy lifting.</h2>
          </div>
          <div className="how-steps">
            <div className="how-step reveal">
              <div className="how-step-num" aria-hidden="true">
                01
              </div>
              <h3>We Audit Your Workflow</h3>
              <p>
                Reach out and tell us about your business. We map out where you&#39;re losing time and which tasks to
                automate first.
              </p>
            </div>
            <div className="how-step reveal">
              <div className="how-step-num" aria-hidden="true">
                02
              </div>
              <h3>We Build &amp; Deploy</h3>
              <p>
                Our team builds your custom AI automations and integrates them with your existing tools (Gmail, Calendly,
                CRM, etc).
              </p>
            </div>
            <div className="how-step reveal">
              <div className="how-step-num" aria-hidden="true">
                03
              </div>
              <h3>You Get Your Time Back</h3>
              <p>Your automations run 24/7. We monitor, optimize, and add new ones as your business grows.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ WHO IT'S FOR ============ */}
      <section className="section" id="who">
        <div className="container">
          <div className="who-header">
            <div className="section-label reveal">Built For</div>
            <h2 className="section-title reveal">Built for businesses like yours.</h2>
          </div>
          <div className="who-grid">
            <div className="who-card reveal">
              <div className="who-card-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
              </div>
              <h3>Real Estate Agents</h3>
              <p>Capture and qualify leads while you&#39;re showing homes.</p>
            </div>
            <div className="who-card reveal">
              <div className="who-card-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              </div>
              <h3>Dental &amp; Medical Offices</h3>
              <p>Automate appointment reminders and patient intake.</p>
            </div>
            <div className="who-card reveal">
              <div className="who-card-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
              </div>
              <h3>Law Firms</h3>
              <p>Triage client inquiries and manage follow-ups.</p>
            </div>
            <div className="who-card reveal">
              <div className="who-card-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
              </div>
              <h3>Home Services</h3>
              <p>Never miss a service request or estimate follow-up.</p>
            </div>
            <div className="who-card reveal">
              <div className="who-card-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
              </div>
              <h3>Fitness &amp; Wellness</h3>
              <p>Automate class bookings, reminders, and re-engagement.</p>
            </div>
            <div className="who-card reveal">
              <div className="who-card-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
              </div>
              <h3>Agencies &amp; Consultants</h3>
              <p>Streamline client onboarding and reporting.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ============ PRICING ============ */}
      <section className="section pricing" id="pricing">
        <div className="container">
          <div className="pricing-header">
            <div className="section-label reveal">Pricing</div>
            <h2 className="section-title reveal">Simple pricing. Serious ROI.</h2>
            <p className="section-subtitle reveal">
              Every plan includes hands-on setup, onboarding, and ongoing support from our team.
            </p>
          </div>
          <div className="pricing-grid">
            {/* Free AI Widget */}
            <div className="pricing-card reveal">
              <div className="pricing-plan-name">Free AI Widget</div>
              <div className="pricing-tagline">Start capturing leads today. Zero cost.</div>
              <div className="pricing-amount">
                <span className="pricing-dollar">$0</span>
                <span className="pricing-period">/month</span>
              </div>
              <div className="pricing-setup">No setup fee</div>
              <div className="pricing-divider"></div>
              <ul className="pricing-features">
                <li>
                  <strong>AI Chatbot Widget</strong>
                  <div className="feat-desc">
                    Embed a conversational chatbot on your website that greets visitors and answers basic questions 24/7.
                  </div>
                </li>
                <li>
                  <strong>Lead Capture Form</strong>
                  <div className="feat-desc">
                    Collects name, email, and phone from visitors. Sends you an instant notification for every new lead.
                  </div>
                </li>
                <li>
                  <strong>Up to 50 Conversations/Month</strong>
                  <div className="feat-desc">
                    Handles up to 50 chatbot conversations per month at no charge. Upgrade anytime for unlimited.
                  </div>
                </li>
                <li>
                  <strong>Easy Install</strong>
                  <div className="feat-desc">
                    Copy-paste one line of code onto your website. Works with any site builder or platform.
                  </div>
                </li>
              </ul>
              <div className="pricing-best">Best for: Anyone who wants to try AI lead capture risk-free</div>
              <a href="/signup" className="pricing-cta">
                Get Started {"\u2192"}
              </a>
            </div>

            {/* Foundation */}
            <div className="pricing-card reveal">
              <div className="pricing-plan-name">Foundation</div>
              <div className="pricing-tagline">Automate the basics. Capture every lead.</div>
              <div className="pricing-amount">
                <span className="pricing-dollar">$99</span>
                <span className="pricing-period">/month</span>
              </div>
              <div className="pricing-setup">$149 one-time setup fee</div>
              <div className="pricing-divider"></div>
              <ul className="pricing-features">
                <li>
                  <strong>AI Lead Capture Chatbot</strong>
                  <div className="feat-desc">
                    Website chatbot that captures name, email, and phone. Qualifies leads and sends info to your CRM or
                    email.
                  </div>
                </li>
                <li>
                  <strong>Automated Review Requests</strong>
                  <div className="feat-desc">
                    After every job, automatically send a text/email with your Google review link. Reminder sent if not
                    completed.
                  </div>
                </li>
                <li>
                  <strong>Missed Call Text-Back</strong>
                  <div className="feat-desc">
                    Missed a call? Leads instantly get &quot;Sorry we missed you&quot; via SMS, automatically.
                  </div>
                </li>
                <li>
                  <strong>Appointment Reminders</strong>
                  <div className="feat-desc">
                    SMS reminders 24 hours and 2 hours before every appointment. Reduces no-shows dramatically.
                  </div>
                </li>
              </ul>
              <div className="pricing-best">Best for: Contractors, med spas, law firms, home services</div>
              <a href="/signup" className="pricing-cta">
                Get Started {"\u2192"}
              </a>
            </div>

            {/* Growth */}
            <div className="pricing-card popular reveal">
              <div className="pricing-plan-name">Growth</div>
              <div className="pricing-tagline">Never lose a lead again.</div>
              <div className="pricing-amount">
                <span className="pricing-dollar">$249</span>
                <span className="pricing-period">/month</span>
              </div>
              <div className="pricing-setup">$399 one-time setup fee</div>
              <div className="pricing-divider"></div>
              <div className="pricing-includes">Everything in Foundation, plus:</div>
              <ul className="pricing-features">
                <li>
                  <strong>Lead Follow-Up Drip System</strong>
                  <div className="feat-desc">
                    New lead comes in, automatic email + text sequence fires. 5-7 AI-personalized touchpoints over 14
                    days.
                  </div>
                </li>
                <li>
                  <strong>AI FAQ &amp; Customer Support Bot</strong>
                  <div className="feat-desc">
                    Trained on your business FAQs. Handles 60-70% of common questions via chat and SMS.
                  </div>
                </li>
                <li>
                  <strong>Quote &amp; Estimate Automation</strong>
                  <div className="feat-desc">
                    Customer fills out a form, AI generates a formatted estimate draft, sends it automatically.
                  </div>
                </li>
                <li>
                  <strong>CRM Setup + Pipeline Automation</strong>
                  <div className="feat-desc">
                    Auto-tag leads, move pipeline stages based on actions, trigger notifications when deals progress.
                  </div>
                </li>
              </ul>
              <div className="pricing-best">Best for: Growing businesses ready to systematize sales</div>
              <a href="/signup" className="pricing-cta">
                Get Started {"\u2192"}
              </a>
            </div>

            {/* Operations */}
            <div className="pricing-card reveal">
              <div className="pricing-plan-name">Operations</div>
              <div className="pricing-tagline">Cut your admin work in half.</div>
              <div className="pricing-amount">
                <span className="pricing-dollar">$499</span>
                <span className="pricing-period">/month</span>
              </div>
              <div className="pricing-setup">$599 one-time setup fee</div>
              <div className="pricing-divider"></div>
              <div className="pricing-includes">Everything in Growth, plus:</div>
              <ul className="pricing-features">
                <li>
                  <strong>AI Appointment Booking Agent</strong>
                  <div className="feat-desc">
                    Conversational booking via chat or SMS. Syncs with Google Calendar. Handles reschedules
                    automatically.
                  </div>
                </li>
                <li>
                  <strong>Invoice &amp; Payment Follow-Up</strong>
                  <div className="feat-desc">
                    Automatic invoice reminders with escalation sequences and late fee reminder logic.
                  </div>
                </li>
                <li>
                  <strong>Internal Task Automation</strong>
                  <div className="feat-desc">
                    Sale closes, auto-create tasks, notify your team, send onboarding emails. Operations on autopilot.
                  </div>
                </li>
                <li>
                  <strong>AI Lead Scoring</strong>
                  <div className="feat-desc">
                    Scores every lead based on behavior and engagement. Alerts you when a lead is hot.
                  </div>
                </li>
              </ul>
              <div className="pricing-best">Best for: Businesses ready to eliminate admin busywork</div>
              <a href="/signup" className="pricing-cta">
                Get Started {"\u2192"}
              </a>
            </div>

            {/* Enterprise */}
            <div className="pricing-card reveal">
              <div className="pricing-plan-name">Enterprise</div>
              <div className="pricing-tagline">Your autonomous growth system.</div>
              <div className="pricing-amount">
                <span className="pricing-dollar">$999</span>
                <span className="pricing-period">/month</span>
              </div>
              <div className="pricing-setup">Custom setup fee</div>
              <div className="pricing-divider"></div>
              <div className="pricing-includes">Everything in Operations, plus:</div>
              <ul className="pricing-features">
                <li>
                  <strong>AI Sales Assistant</strong>
                  <div className="feat-desc">
                    Handles inbound inquiries via text and email. Books calls, follows up, escalates only when needed.
                  </div>
                </li>
                <li>
                  <strong>Full Marketing Automation Engine</strong>
                  <div className="feat-desc">
                    Ad lead intake, SMS + email nurturing, retargeting, review requests, and upsell campaigns. Everything
                    connected.
                  </div>
                </li>
                <li>
                  <strong>AI Ops Dashboard</strong>
                  <div className="feat-desc">
                    Real-time view of leads, conversion rates, revenue, and pipeline. Weekly automated reports.
                  </div>
                </li>
                <li>
                  <strong>Re-Engagement Campaign Engine</strong>
                  <div className="feat-desc">
                    Identifies past customers, AI writes personalized offers, sends campaigns, and books appointments.
                  </div>
                </li>
              </ul>
              <div className="pricing-best">Best for: Businesses ready for full AI-powered growth</div>
              <a href={CALENDLY_URL} className="pricing-cta">
                Contact Sales {"\u2192"}
              </a>
            </div>
          </div>
          <p className="pricing-footer-note reveal">
            All plans include done-for-you setup, onboarding, and ongoing optimization. No technical skills required.
            Cancel anytime.
          </p>
        </div>
      </section>

      {/* ============ RESOURCES ============ */}
      <section className="section" id="resources">
        <div className="container">
          <div className="testimonials-header">
            <h2 className="section-title reveal">Resources to help you grow.</h2>
          </div>
          <div className="testimonials-grid">
            <div className="testimonial-card reveal">
              <div className="testimonial-deco" aria-hidden="true">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              </div>
              <h3 className="testimonial-author">Getting Started Guide</h3>
              <p className="testimonial-quote">
                Everything you need to know about setting up your AI automations, connecting your tools, and getting the
                most out of Agent NexLiFy from day one.
              </p>
              <div className="testimonial-since">5 min read</div>
            </div>
            <div className="testimonial-card reveal">
              <div className="testimonial-deco" aria-hidden="true">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
              </div>
              <h3 className="testimonial-author">Automation Playbooks</h3>
              <p className="testimonial-quote">
                Step by step guides for the most popular automations. Lead follow up, missed call handling, review
                generation, appointment scheduling, and more.
              </p>
              <div className="testimonial-since">Updated monthly</div>
            </div>
            <div className="testimonial-card reveal">
              <div className="testimonial-deco" aria-hidden="true">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
              </div>
              <h3 className="testimonial-author">AI for Business Blog</h3>
              <p className="testimonial-quote">
                Practical tips, real world examples, and honest advice on using AI to save time and grow your business
                without the jargon or hype.
              </p>
              <div className="testimonial-since">New posts weekly</div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ ABOUT US ============ */}
      <section className="section" id="about-us">
        <div className="container about-inner">
          <div className="section-label reveal">About Us</div>
          <h2 className="section-title reveal">The people behind Agent NexLiFy.</h2>
          <p className="about-body reveal">
            We&#39;re a team of builders, problem-solvers, and AI specialists who believe every business deserves access
            to the tools that were once reserved for big corporations. We started Agent NexLiFy because we saw business
            owners spending too much time on tasks that technology could handle, and not enough time on the work that
            matters to them and their customers. We&#39;re based in the US, we answer our own emails (well, most of
            them. We automated the rest), and we treat every business we work with like a true partner.
          </p>
          <a href="#cta" className="about-link reveal">
            Want to learn more about our story? Get in touch {"\u2192"}
          </a>
        </div>
      </section>

      {/* ============ FAQ ============ */}
      <section className="section faq" id="faq">
        <div className="container">
          <div className="faq-header">
            <h2 className="section-title reveal">Questions? We&#39;ve got answers.</h2>
          </div>
          <div className="faq-list reveal" role="list">
            {faqData.map((item) => (
              <div className="faq-item" role="listitem" key={item.id}>
                <button
                  className="faq-question"
                  aria-expanded={openFaq === item.id ? "true" : "false"}
                  aria-controls={item.id}
                  onClick={() => handleFaqToggle(item.id)}
                >
                  {item.question}
                  <svg
                    className="faq-chevron"
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
                  className="faq-answer"
                  id={item.id}
                  role="region"
                  ref={(el) => {
                    faqRefs.current[item.id] = el;
                  }}
                  style={{ maxHeight: getFaqMaxHeight(item.id) }}
                >
                  <div className="faq-answer-inner">{item.answer}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ CTA ============ */}
      <section className="cta-section" id="cta">
        <div className="container cta-content">
          <h2 className="section-title reveal">Ready to get back to doing what you love?</h2>
          <p className="section-subtitle reveal">
            Reach out and tell us about your business. We&#39;ll walk you through exactly how we can help.
          </p>
          <div className="hero-buttons reveal" style={{ marginBottom: 0 }}>
            <a href={CALENDLY_URL} className="btn-primary">
              Book a Strategy Call {"\u2192"}
            </a>
            <a href="#pricing" className="btn-secondary">
              See Pricing {"\u2193"}
            </a>
          </div>
          <p className="cta-note reveal">No commitment. No pressure. Just a conversation.</p>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <footer className="footer">
        <div className="container">
          <div className="footer-inner">
            <div className="footer-brand">
              <img src="/logo.png" alt="Agent NexLiFy Logo" className="footer-brand-logo" />
              <p>AI-powered operations for businesses.</p>
              <a
                href={CALENDLY_URL}
                className="btn-primary"
                style={{ marginTop: "16px", fontSize: "14px", padding: "12px 24px" }}
              >
                Book a Strategy Call {"\u2192"}
              </a>
            </div>
            <div className="footer-col">
              <h4>Product</h4>
              <ul>
                <li>
                  <a href="#features">Features</a>
                </li>
                <li>
                  <a href="#pricing">Pricing</a>
                </li>
                <li>
                  <a href="#faq">FAQ</a>
                </li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>Compare</h4>
              <ul>
                <li>
                  <Link to="/intercom-alternative">vs. Intercom</Link>
                </li>
                <li>
                  <Link to="/livechat-alternative">vs. LiveChat</Link>
                </li>
                <li>
                  <Link to="/tidio-alternative">vs. Tidio</Link>
                </li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>Company</h4>
              <ul>
                <li>
                  <a href="#why">Why Us</a>
                </li>
                <li>
                  <a href="#about-us">About</a>
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
                  <a href="#">Privacy Policy</a>
                </li>
                <li>
                  <a href="#">Terms of Service</a>
                </li>
              </ul>
            </div>
          </div>
          <div className="footer-bottom">
            <span className="footer-copy">&copy; 2026 Agent NexLiFy. All rights reserved.</span>
            <div className="footer-socials">
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
    </>
  );
}
