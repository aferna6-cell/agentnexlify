import { useState, useRef, useEffect, useCallback } from 'react';
import demoConfig from '../config/demoConfig';

const faqKnowledge = demoConfig.faqKnowledge;

function matchFaq(input) {
  const lower = input.toLowerCase();
  let bestMatch = null;
  let bestScore = 0;

  for (const [, entry] of Object.entries(faqKnowledge)) {
    let score = 0;
    for (const kw of entry.keywords) {
      if (lower.includes(kw)) score++;
    }
    if (score > bestScore) {
      bestScore = score;
      bestMatch = entry.response;
    }
  }

  return bestMatch || "Great question! I don't have that specific info, but I can have someone from our team get back to you. Can I grab your name and email?";
}

export default function FAQBot() {
  const [messages, setMessages] = useState([
    { role: 'bot', text: demoConfig.faqGreeting },
  ]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [stats, setStats] = useState({ handled: 0, escalated: 0, timeSaved: 0 });
  const [useApi, setUseApi] = useState(false);
  const messagesEnd = useRef(null);

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((data) => setUseApi(data.ai_enabled === true))
      .catch(() => setUseApi(false));
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  const handleSend = useCallback(async (text) => {
    const msg = text || input.trim();
    if (!msg || typing) return;

    const newMessages = [...messages, { role: 'user', text: msg }];
    setMessages(newMessages);
    setInput('');
    setTyping(true);

    let response;

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
            system: demoConfig.faqSystemPrompt,
          }),
        });
        const data = await res.json();
        response = data.response || data.error || 'Sorry, something went wrong.';
      } catch {
        response = matchFaq(msg);
      }
    } else {
      response = matchFaq(msg);
    }

    const isEscalated = response.includes("don't have that specific info");

    setTyping(false);
    setMessages((prev) => [...prev, { role: 'bot', text: response }]);
    setStats((prev) => ({
      handled: prev.handled + (isEscalated ? 0 : 1),
      escalated: prev.escalated + (isEscalated ? 1 : 0),
      timeSaved: prev.timeSaved + (isEscalated ? 0 : 3),
    }));
  }, [input, messages, typing, useApi]);

  return (
    <>
      <div className="page-header">
        <h1>AI Customer Support Bot — Demo</h1>
        <p>Trained on {demoConfig.bizName} FAQ. Ask anything.</p>
      </div>

      <div className="faq-container">
        <div className="faq-stats">
          <div className="faq-stat">
            {'\uD83E\uDD16'} Handled by AI: <span className="faq-stat-value">{stats.handled}</span>
          </div>
          <div className="faq-stat">
            {'\uD83D\uDC64'} Escalated to human: <span className="faq-stat-value">{stats.escalated}</span>
          </div>
          <div className="faq-stat">
            {'\u23F1\uFE0F'} Time saved: <span className="faq-stat-value">~{stats.timeSaved} min</span>
          </div>
        </div>

        <div className="faq-quick-buttons">
          {demoConfig.quickQuestions.map((q) => (
            <button key={q} className="faq-quick-btn" onClick={() => handleSend(q)}>
              {q}
            </button>
          ))}
        </div>

        <div className="chat-widget" style={{ flex: 1 }}>
          <div className="chat-header">
            <img src="/logo.png" alt="Logo" />
            <div>
              <div className="chat-header-title">FAQ Support Bot</div>
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
              placeholder="Ask a question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button className="chat-send" onClick={() => handleSend()} aria-label="Send">{'\u27A4'}</button>
          </div>
        </div>
      </div>
    </>
  );
}
