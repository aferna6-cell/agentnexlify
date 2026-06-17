import { useState, useRef, useEffect, useCallback } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import "../styles/home.css";

/*
 * /demo - hands-on interactive product sample.
 *
 * Self-contained: no backend, no auth, no API calls. The visitor drives
 * the product surfaces themselves (tabs), types in a live chat that
 * answers with canned keyword-matched replies, and browses the mock
 * leads + calendar. Ends with a sign-up CTA.
 *
 * Reuses the demo-* and ds-* design language from Home.jsx DemoPreview.
 */

const demoTabs = [
  { key: "workforce", label: "AI Workforce" },
  { key: "frontdesk", label: "Front Desk" },
  { key: "leads", label: "Leads" },
  { key: "automations", label: "Automations" },
  { key: "calendar", label: "Calendar" },
];

const TAB_HINTS = {
  workforce: "Type a request to your AI manager, or pick a suggestion.",
  frontdesk: "You are the customer. Type a message to the AI Front Desk.",
  leads: "Sort and filter the way your team would after a busy week.",
  automations: "Toggle steps to see how a follow-up sequence runs itself.",
  calendar: "Bookings the AI made land here automatically.",
};

/* ----- AI Workforce (manager thread) ----- */

const WORKFORCE_PROMPTS = [
  "Follow up with yesterday's quote lead",
  "What's on my calendar this week?",
  "Draft a review request for Sarah",
];

function workforceReply(text) {
  const t = text.toLowerCase();
  if (t.includes("calendar") || t.includes("week") || t.includes("schedule"))
    return {
      dept: "Operations",
      body: "3 appointments this week: Mon 9 AM Sarah J., Wed 11 AM James W., Thu 2 PM new consult. 2 invoices outstanding totaling $4,200.",
    };
  if (t.includes("review") || t.includes("sarah"))
    return {
      dept: "Reputation",
      body: 'Sarah Johnson closed 3 days ago and rated the visit 5 stars. Draft: "Hi Sarah, glad the project went well. Would you mind leaving a quick Google review? Here is the link." Ready to send.',
    };
  if (t.includes("quote") || t.includes("follow") || t.includes("lead"))
    return {
      dept: "Sales",
      body: 'Found Mike Chen from yesterday. He asked about kitchen remodel pricing. Draft: "Hi Mike, just checking in on the kitchen quote we discussed. Happy to schedule a walkthrough."',
    };
  if (t.includes("invoice") || t.includes("pay") || t.includes("owe"))
    return {
      dept: "Billing",
      body: "2 invoices outstanding: Lisa Park $1,800 (12 days), James Wilson $2,400 (4 days). Want me to send payment reminders?",
    };
  return {
    dept: "Manager",
    body: "Routed to the right department. In the full product I can act across sales, scheduling, billing, and reputation from one chat. Try asking about your calendar, a follow-up, or a review.",
  };
}

function WorkforcePanel() {
  const [thread, setThread] = useState([
    { role: "user", text: "Follow up with the lead from yesterday who asked about a quote" },
    {
      role: "bot",
      dept: "Sales",
      text: 'Found Mike Chen from yesterday. He asked about kitchen remodel pricing. Draft: "Hi Mike, just checking in on the kitchen quote we discussed. Happy to schedule a walkthrough."',
      draft: true,
    },
  ]);
  const [input, setInput] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [thread]);

  const send = useCallback((raw) => {
    const text = (raw ?? "").trim();
    if (!text) return;
    setInput("");
    setThread((prev) => [...prev, { role: "user", text }]);
    const reply = workforceReply(text);
    setTimeout(() => {
      setThread((prev) => [
        ...prev,
        { role: "bot", dept: reply.dept, text: reply.body },
      ]);
    }, 450);
  }, []);

  return (
    <div className="ds-agent-os de-interactive">
      <div className="ds-os-thread de-scroll">
        {thread.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="ds-os-msg ds-os-msg-user">
              {m.text}
            </div>
          ) : (
            <div key={i} className="ds-os-msg ds-os-msg-bot">
              <span className="ds-os-dept">{m.dept}</span>
              {m.text}
              {m.draft && (
                <div className="ds-os-actions">
                  <span className="ds-os-btn ds-os-btn-approve">Approve &amp; Send</span>
                  <span className="ds-os-btn ds-os-btn-edit">Edit</span>
                </div>
              )}
            </div>
          ),
        )}
        <div ref={endRef} />
      </div>
      <div className="de-suggestions">
        {WORKFORCE_PROMPTS.map((p) => (
          <button key={p} className="de-chip" onClick={() => send(p)}>
            {p}
          </button>
        ))}
      </div>
      <form
        className="de-input-row"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <label htmlFor="de-workforce-input" className="de-visually-hidden">
          Ask your AI manager
        </label>
        <input
          id="de-workforce-input"
          className="de-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your AI manager..."
          autoComplete="off"
        />
        <button type="submit" className="de-send" aria-label="Send">
          {"->"}
        </button>
      </form>
    </div>
  );
}

/* ----- Front Desk (customer-facing chat) ----- */

function frontDeskReply(text) {
  const t = text.toLowerCase();
  if (t.includes("book") || t.includes("schedule") || t.includes("appointment") || t.includes("consult"))
    return "Of course. What day works best for you? I have openings Thursday at 2 PM and Friday at 10 AM.";
  if (t.includes("thursday") || t.includes("friday") || t.includes("2pm") || t.includes("2 pm") || t.includes("10am"))
    return "Booked. You'll get a confirmation by text and email shortly. Anything else I can help with?";
  if (t.includes("price") || t.includes("cost") || t.includes("quote") || t.includes("how much"))
    return "Most kitchen consultations are free, and we send a written quote within 24 hours. Want me to set one up?";
  if (t.includes("hour") || t.includes("open") || t.includes("close"))
    return "We're open Monday to Friday, 8 AM to 6 PM, and Saturday 9 AM to 1 PM. Want to book a time?";
  if (t.includes("human") || t.includes("agent") || t.includes("person") || t.includes("call"))
    return "I can take your name and number and have the team call you back within the hour. What's the best number to reach you?";
  if (t.includes("hi") || t.includes("hello") || t.includes("hey"))
    return "Hi there. I can answer questions, give a quote, or book you in. What brings you by today?";
  return "Happy to help with that. I can answer questions, give a quote, or book an appointment. Which would you like?";
}

function FrontDeskPanel() {
  const [thread, setThread] = useState([
    { role: "bot", text: "Hi! How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [thread]);

  const send = useCallback((raw) => {
    const text = (raw ?? "").trim();
    if (!text) return;
    setInput("");
    setThread((prev) => [...prev, { role: "user", text }]);
    const reply = frontDeskReply(text);
    setTimeout(() => {
      setThread((prev) => [...prev, { role: "bot", text: reply }]);
    }, 450);
  }, []);

  return (
    <div className="ds-chat de-interactive">
      <div className="ds-chat-window de-chat-window">
        <div className="ds-chat-header">
          <span className="ds-chat-status" />
          AI Front Desk - Online 24/7
        </div>
        <div className="ds-chat-body de-scroll">
          {thread.map((m, i) => (
            <div key={i} className={`ds-msg ${m.role === "user" ? "user" : "bot"}`}>
              {m.text}
            </div>
          ))}
          <div ref={endRef} />
        </div>
        <form
          className="de-chat-input-row"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <label htmlFor="de-frontdesk-input" className="de-visually-hidden">
            Message the AI Front Desk
          </label>
          <input
            id="de-frontdesk-input"
            className="de-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            autoComplete="off"
          />
          <button type="submit" className="de-send" aria-label="Send">
            {"->"}
          </button>
        </form>
      </div>
    </div>
  );
}

/* ----- Leads (sortable mock table) ----- */

const LEADS = [
  { name: "Sarah Johnson", score: 92, stage: "Hot", tag: "hot", contact: "2 hrs ago", order: 0 },
  { name: "Mike Chen", score: 74, stage: "Warm", tag: "warm", contact: "1 day ago", order: 1 },
  { name: "Emily Davis", score: 88, stage: "New", tag: "new", contact: "Just now", order: 2 },
  { name: "James Wilson", score: 45, stage: "Cold", tag: "cold", contact: "5 days ago", order: 3 },
  { name: "Lisa Park", score: 67, stage: "Warm", tag: "warm", contact: "3 hrs ago", order: 4 },
];

function scoreClass(score) {
  if (score >= 80) return "high";
  if (score >= 60) return "med";
  return "low";
}

function LeadsPanel() {
  const [sortBy, setSortBy] = useState("score");
  const [filter, setFilter] = useState("all");

  const rows = LEADS.filter((l) =>
    filter === "all" ? true : l.tag === filter,
  ).sort((a, b) => {
    if (sortBy === "score") return b.score - a.score;
    if (sortBy === "name") return a.name.localeCompare(b.name);
    return a.order - b.order;
  });

  return (
    <div className="ds-clients de-interactive">
      <div className="de-leads-controls">
        <div className="de-control">
          <label htmlFor="de-sort" className="de-control-label">
            Sort by
          </label>
          <select
            id="de-sort"
            className="de-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="score">Lead score</option>
            <option value="name">Name</option>
            <option value="recent">Most recent</option>
          </select>
        </div>
        <div className="de-control">
          <label htmlFor="de-filter" className="de-control-label">
            Stage
          </label>
          <select
            id="de-filter"
            className="de-select"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All stages</option>
            <option value="hot">Hot</option>
            <option value="warm">Warm</option>
            <option value="new">New</option>
            <option value="cold">Cold</option>
          </select>
        </div>
      </div>
      <div className="ds-table">
        <div className="ds-table-head">
          <span>Name</span>
          <span>Score</span>
          <span>Stage</span>
          <span>Last Contact</span>
        </div>
        {rows.length === 0 ? (
          <div className="de-empty">No leads in this stage yet. Pick another filter.</div>
        ) : (
          rows.map((l) => (
            <div className="ds-table-row" key={l.name}>
              <span>{l.name}</span>
              <span className={`ds-score ${scoreClass(l.score)}`}>{l.score}</span>
              <span className={`ds-tag ${l.tag}`}>{l.stage}</span>
              <span>{l.contact}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ----- Automations (toggleable sequence) ----- */

const SEQUENCE = [
  { id: 1, name: "Welcome Email", when: "Sent immediately" },
  { id: 2, name: "Case Study", when: "After 2 days" },
  { id: 3, name: "Check-In", when: "After 5 days" },
  { id: 4, name: "Special Offer", when: "After 10 days" },
];

function AutomationsPanel() {
  // Steps up to and including `enabled` count as active in the sequence.
  const [enabled, setEnabled] = useState(2);

  return (
    <div className="ds-automations de-interactive">
      <div className="ds-panel-title">Follow-Up Sequence: New Lead</div>
      <div className="ds-sequence">
        {SEQUENCE.map((step, idx) => {
          const isOn = idx <= enabled;
          const isCurrent = idx === enabled;
          const status = isCurrent ? "Pending" : isOn ? "Sent" : "Scheduled";
          const statusClass = isCurrent ? "pending" : isOn ? "sent" : "";
          return (
            <div key={step.id}>
              <button
                type="button"
                className={`ds-step de-step-toggle${isOn ? "" : " dim"}${isCurrent ? " current" : ""}`}
                onClick={() => setEnabled(idx)}
                aria-pressed={isOn}
              >
                <span className={`ds-step-badge${isCurrent ? " pulse" : ""}`}>
                  {step.id}
                </span>
                <span className="ds-step-info">
                  <strong>{step.name}</strong>
                  <span>{step.when}</span>
                </span>
                <span className={`ds-step-status ${statusClass}`}>{status}</span>
              </button>
              {idx < SEQUENCE.length - 1 && (
                <div className={`ds-step-line${idx < enabled ? "" : " dim"}`} />
              )}
            </div>
          );
        })}
      </div>
      <div className="de-note">
        Click a step to set how far the sequence has run. The AI sends each
        message on time without anyone lifting a finger.
      </div>
    </div>
  );
}

/* ----- Calendar (selectable bookings) ----- */

const WEEK = [
  { day: "Mon", events: [{ label: "9:00 - Sarah J.", color: "blue" }, { label: "2:00 - Mike C.", color: "green" }] },
  { day: "Tue", events: [{ label: "10:30 - Emily D.", color: "purple" }] },
  { day: "Wed", events: [{ label: "11:00 - James W.", color: "blue" }, { label: "3:30 - Lisa P.", color: "green" }] },
  { day: "Thu", events: [{ label: "2:00 - New Consult", color: "accent" }] },
  { day: "Fri", events: [{ label: "9:30 - Follow-up", color: "blue" }] },
];

function CalendarPanel() {
  const [selected, setSelected] = useState(null);

  return (
    <div className="ds-calendar de-interactive">
      <div className="ds-panel-title">This Week - March 2026</div>
      <div className="ds-cal-grid">
        {WEEK.map((col) => (
          <div className="ds-cal-col" key={col.day}>
            <div className="ds-cal-day">{col.day}</div>
            <div className="ds-cal-slots">
              {col.events.map((ev) => {
                const id = `${col.day}-${ev.label}`;
                return (
                  <button
                    key={id}
                    type="button"
                    className={`ds-cal-event ${ev.color} de-cal-event${selected === id ? " de-selected" : ""}`}
                    onClick={() => setSelected(selected === id ? null : id)}
                  >
                    {ev.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="de-note">
        {selected
          ? `${selected.split("-").slice(1).join("-").trim()} on ${selected.split("-")[0]} - booked by the AI, synced to your calendar.`
          : "Pick any appointment. Every booking the AI makes shows up here and on your real calendar."}
      </div>
    </div>
  );
}

function ActivePanel({ tab }) {
  if (tab === "workforce") return <WorkforcePanel />;
  if (tab === "frontdesk") return <FrontDeskPanel />;
  if (tab === "leads") return <LeadsPanel />;
  if (tab === "automations") return <AutomationsPanel />;
  if (tab === "calendar") return <CalendarPanel />;
  return null;
}

export default function DemoExperience() {
  const [active, setActive] = useState("workforce");
  const activeLabel =
    demoTabs.find((t) => t.key === active)?.label || "AI Workforce";

  return (
    <div className="landing-page de-page">
      <Helmet>
        <title>Interactive Demo | AgentNexLiFy</title>
        <meta
          name="description"
          content="Try AgentNexLiFy hands-on. Drive the AI Workforce, chat with the AI Front Desk, browse leads, automations, and the calendar. No sign-up needed."
        />
        <link rel="canonical" href="https://agentnexlify.com/demo" />
        <meta name="robots" content="index,follow" />
      </Helmet>

      <nav className="lp-nav scrolled" role="navigation" aria-label="Demo navigation">
        <div className="lp-nav-inner">
          <a href="/" className="lp-nav-logo">
            <img src="/logo.png" alt="Agent NexLiFy" />
            <span>NexLiFy</span>
          </a>
          <div className="lp-nav-actions">
            <a href="/" className="lp-nav-login">
              <span>Back to home</span>
            </a>
            <Link to="/signup" className="lp-nav-cta">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <section className="section de-hero">
        <div className="container">
          <div className="de-hero-inner">
            <div className="section-label">Interactive Demo</div>
            <h1 className="section-title">Try the product yourself.</h1>
            <p className="section-subtitle de-hero-sub">
              Click between the surfaces below. Chat with the AI Front Desk,
              give the AI manager a task, sort your leads, and browse the
              calendar. Nothing to install, no sign-up.
            </p>
          </div>
        </div>
      </section>

      <section className="section de-stage-section">
        <div className="container">
          <div className="demo-preview-wrap de-wide">
            <div className="demo-browser">
              <div className="demo-browser-bar">
                <span className="demo-dot" />
                <span className="demo-dot" />
                <span className="demo-dot" />
                <span className="demo-url">app.agentnexlify.com/{active}</span>
              </div>
              <div className="demo-screen">
                <div className="demo-sidebar">
                  <div className="demo-sidebar-logo">NexLiFy</div>
                  {demoTabs.map((t) => (
                    <button
                      key={t.key}
                      className={`demo-sidebar-item${t.key === active ? " active" : ""}`}
                      onClick={() => setActive(t.key)}
                      aria-current={t.key === active ? "page" : undefined}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
                <div className="demo-main de-main">
                  <div className="de-panel-head">
                    <span className="de-panel-name">{activeLabel}</span>
                    <span className="de-panel-hint">{TAB_HINTS[active]}</span>
                  </div>
                  <div className="de-panel-body">
                    <ActivePanel tab={active} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="de-cta">
            <h2 className="de-cta-title">Ready to put your AI staff to work?</h2>
            <p className="de-cta-sub">
              This is the real product running on sample data. Start free and
              connect your own widget, leads, and calendar in minutes.
            </p>
            <div className="de-cta-actions">
              <Link to="/signup" className="lp-btn-primary">
                Start free {"->"}
              </Link>
              <Link to="/contact" className="lp-btn-secondary">
                Talk to us
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="container">
          <div className="lp-footer-bottom">
            <span className="lp-footer-copy">
              &copy; 2026 Agent NexLiFy. All rights reserved.
            </span>
            <span className="de-footer-links">
              <a href="/">Home</a>
              <Link to="/contact">Contact</Link>
              <Link to="/privacy">Privacy</Link>
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
