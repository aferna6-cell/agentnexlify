import { useState, useRef, useEffect, useCallback } from 'react';
import { chatSimulation } from '../data/mockData';

const SYSTEM_PROMPT = `You are a friendly AI assistant for a home services company called "Smith's Home Solutions" in Austin, TX. You help capture leads and answer questions.

Services offered: Plumbing, HVAC, Electrical, Kitchen/Bath Remodeling
Hours: Mon-Fri 7am-6pm, Sat 8am-2pm, Emergency service 24/7
Service area: Austin metro area, within 30 miles

Your job:
1. Greet warmly and ask how you can help
2. Understand what service they need
3. Capture their name, phone, and email (give a reason: "so we can send you a detailed quote")
4. Ask about timeline and budget range
5. Offer to book an appointment
6. Be conversational, not robotic

When you capture contact info, confirm it back to them.`;

function extractInfo(messages) {
  const info = { name: '', email: '', phone: '', service: '', budget: '', timeline: '' };
  const userMsgs = messages.filter((m) => m.role === 'user').map((m) => m.text).join(' ');

  // Name
  const nameMatch = userMsgs.match(/(?:(?:i'm|im|i am|my name is|this is|name's|call me)\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/i);
  if (nameMatch) info.name = nameMatch[1];

  // Email
  const emailMatch = userMsgs.match(/[\w.+-]+@[\w-]+\.[\w.]+/);
  if (emailMatch) info.email = emailMatch[0];

  // Phone
  const phoneMatch = userMsgs.match(/(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/);
  if (phoneMatch) info.phone = phoneMatch[0];

  // Service
  const services = { plumbing: 'Plumbing', hvac: 'HVAC', heating: 'HVAC', cooling: 'HVAC', 'air conditioning': 'HVAC', electrical: 'Electrical', kitchen: 'Kitchen Remodel', bath: 'Bath Remodel', remodel: 'Remodeling' };
  for (const [kw, svc] of Object.entries(services)) {
    if (userMsgs.toLowerCase().includes(kw)) { info.service = svc; break; }
  }

  // Budget
  const budgetMatch = userMsgs.match(/\$[\d,]+(?:k)?/i) || userMsgs.match(/(\d{1,3}(?:,\d{3})*)\s*(?:dollars|budget)/i);
  if (budgetMatch) info.budget = budgetMatch[0];

  // Timeline
  const timelineKws = { asap: 'ASAP', urgent: 'Urgent', 'this week': 'This week', 'next week': 'Next week', 'this month': 'This month', 'few months': 'Few months' };
  for (const [kw, tl] of Object.entries(timelineKws)) {
    if (userMsgs.toLowerCase().includes(kw)) { info.timeline = tl; break; }
  }

  return info;
}

function computeLeadScore(info) {
  let score = 0;
  let label = 'Cold';
  if (info.service) { score += 25; label = 'Warm'; }
  if (info.name) score += 15;
  if (info.phone || info.email) { score += 30; label = 'Hot'; }
  if (info.budget) score += 15;
  if (info.timeline) score += 15;
  return { score: Math.min(score, 100), label };
}

function getTriggeredAutomations(info) {
  return [
    { label: 'Lead captured in CRM', done: !!(info.name || info.email || info.phone) },
    { label: 'Notification sent to business owner', done: !!(info.phone || info.email) },
    { label: 'Follow-up sequence scheduled', done: !!info.email },
    { label: 'Appointment booking link sent', done: !!info.timeline },
    { label: 'Review request queued', done: false },
  ];
}

function getSuggestedActions(info) {
  const actions = [];
  if (info.service) actions.push(`Send detailed quote for ${info.service.toLowerCase()}`);
  if (info.name) actions.push('Schedule follow-up call for tomorrow');
  if (info.service === 'HVAC') actions.push('Add to HVAC remarketing list');
  if (info.service === 'Kitchen Remodel') actions.push('Send kitchen remodel portfolio');
  if (!actions.length) actions.push('Engage lead to identify service need');
  return actions;
}

// Simulated response logic when no API key
function getSimulatedResponse(messages) {
  const lastUser = messages.filter((m) => m.role === 'user').slice(-1)[0]?.text?.toLowerCase() || '';
  const allUser = messages.filter((m) => m.role === 'user').map((m) => m.text.toLowerCase()).join(' ');
  const turnCount = messages.filter((m) => m.role === 'user').length;

  // Extract name for personalization
  const nameMatch = allUser.match(/(?:i'm|im|i am|my name is|this is|call me)\s+([a-z]+)/i);
  const name = nameMatch ? nameMatch[1].charAt(0).toUpperCase() + nameMatch[1].slice(1) : '';

  // Detect if name was just given
  const justGaveName = lastUser.match(/(?:i'm|im|i am|my name is|this is|call me)\s+[a-z]+/i);
  if (justGaveName && name) return chatSimulation.nameCapture(name);

  // Detect phone number
  if (lastUser.match(/\d{3}[-.\s]?\d{3}[-.\s]?\d{4}/)) return chatSimulation.phoneCapture;

  // Detect email
  if (lastUser.match(/[\w.+-]+@[\w-]+\.\w+/)) return chatSimulation.emailCapture;

  // Detect scheduling intent
  if (lastUser.match(/(?:yes|yeah|sure|book|schedule|appointment|sounds good)/i) && turnCount > 3) return chatSimulation.scheduling;

  // Detect service inquiry
  if (lastUser.match(/(?:plumbing|hvac|kitchen|remodel|bath|electrical|heating|cooling|air conditioning|leak|repair|install)/i)) {
    return chatSimulation.serviceInquiry;
  }

  // General greeting
  if (turnCount === 1 || lastUser.match(/(?:hi|hello|hey|good morning|good afternoon)/i)) {
    return chatSimulation.greeting;
  }

  // Closing
  if (lastUser.match(/(?:thanks|thank you|no|nothing|bye|that's all|that's it)/i) && turnCount > 2) {
    return chatSimulation.closing;
  }

  return chatSimulation.fallback;
}

export default function LiveChat() {
  const [messages, setMessages] = useState([
    { role: 'bot', text: chatSimulation.greeting },
  ]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [useApi, setUseApi] = useState(null); // null = not checked yet
  const messagesEnd = useRef(null);

  useEffect(() => {
    // Check if API backend is available
    fetch('/api/health').then((r) => {
      setUseApi(r.ok);
    }).catch(() => setUseApi(false));
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || typing) return;

    const newMessages = [...messages, { role: 'user', text }];
    setMessages(newMessages);
    setInput('');
    setTyping(true);

    if (useApi) {
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: newMessages.map((m) => ({
              role: m.role === 'bot' ? 'assistant' : 'user',
              content: m.text,
            })),
            system: SYSTEM_PROMPT,
          }),
        });
        const data = await res.json();
        setTyping(false);
        setMessages((prev) => [...prev, { role: 'bot', text: data.response || data.error || 'Sorry, something went wrong.' }]);
      } catch {
        setTyping(false);
        // Fallback to simulated
        const reply = getSimulatedResponse(newMessages);
        setMessages((prev) => [...prev, { role: 'bot', text: reply }]);
      }
    } else {
      // Simulated response with typing delay
      setTimeout(() => {
        const reply = getSimulatedResponse(newMessages);
        setTyping(false);
        setMessages((prev) => [...prev, { role: 'bot', text: reply }]);
      }, 800 + Math.random() * 800);
    }
  }, [input, messages, typing, useApi]);

  const info = extractInfo(messages);
  const leadScore = computeLeadScore(info);
  const automations = getTriggeredAutomations(info);
  const suggestions = getSuggestedActions(info);

  const scoreColor = leadScore.label === 'Hot' ? 'var(--red)' : leadScore.label === 'Warm' ? 'var(--yellow)' : 'var(--accent)';

  return (
    <>
      <div className="page-header">
        <h1>Live Chat</h1>
        <p>Interactive AI chatbot demo {useApi === true ? '— Connected to AI backend' : useApi === false ? '— Simulated responses' : '— Checking backend...'}</p>
      </div>

      <div className="chat-layout">
        {/* Chat Widget */}
        <div className="chat-widget">
          <div className="chat-header">
            <img src="/logo.png" alt="Logo" />
            <div>
              <div className="chat-header-title">AgentNexLiFy AI Assistant</div>
              <div className="chat-header-status">
                <span className="chat-header-dot" />
                Online
              </div>
            </div>
          </div>

          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.role === 'bot' ? 'bot' : 'user'}`}>
                {msg.text}
              </div>
            ))}
            {typing && (
              <div className="chat-typing">
                <span /><span /><span />
              </div>
            )}
            <div ref={messagesEnd} />
          </div>

          <div className="chat-input-area">
            <input
              className="chat-input"
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            />
            <button className="chat-send" onClick={sendMessage} aria-label="Send">{'\u27A4'}</button>
          </div>
        </div>

        {/* Lead Intelligence Panel */}
        <div className="lead-intel">
          <div className="intel-section">
            <div className="intel-title">Lead Score</div>
            <div className="lead-score-display">
              <div style={{ flex: 1 }}>
                <div className="lead-score-label">Current Score</div>
                <div className="lead-score-value" style={{ color: scoreColor }}>
                  {leadScore.score}/100 — {leadScore.label}
                </div>
              </div>
              <div style={{ fontSize: 32 }}>
                {leadScore.label === 'Hot' ? '\u{1F525}' : leadScore.label === 'Warm' ? '\u{1F7E1}' : '\u{1F535}'}
              </div>
            </div>
          </div>

          <div className="intel-section">
            <div className="intel-title">Lead Profile</div>
            {[
              ['Name', info.name],
              ['Email', info.email],
              ['Phone', info.phone],
              ['Service Needed', info.service],
              ['Budget', info.budget],
              ['Timeline', info.timeline],
            ].map(([label, value]) => (
              <div className="intel-row" key={label}>
                <span className="intel-label">{label}</span>
                <span className={`intel-value ${value ? '' : 'empty'}`}>
                  {value || 'Waiting...'}
                </span>
              </div>
            ))}
          </div>

          <div className="intel-section">
            <div className="intel-title">Automations Triggered</div>
            <div className="automation-checks">
              {automations.map((a, i) => (
                <div key={i} className={`auto-check ${a.done ? 'done' : 'pending'}`}>
                  {a.done ? '\u2611\uFE0F' : '\u2610'} {a.label}
                </div>
              ))}
            </div>
          </div>

          <div className="intel-section">
            <div className="intel-title">Suggested Actions</div>
            <div className="suggested-actions">
              {suggestions.map((s, i) => (
                <div key={i} className="suggested-action">{s}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
