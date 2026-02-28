import { useState, useRef, useEffect, useCallback } from 'react';

const SIMULATED_REPLIES = [
  "Thanks for reaching out! I'd be happy to help you with that.",
  "Great question! Let me look into that for you.",
  "I can definitely assist with that. Could you tell me a bit more?",
  "Absolutely! Here's what I'd recommend...",
  "That's a common question. Here's what you need to know.",
];

export default function MiniChat({ config }) {
  const [messages, setMessages] = useState([
    { role: 'bot', text: config.greeting },
  ]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const messagesEnd = useRef(null);
  const prevGreeting = useRef(config.greeting);

  useEffect(() => {
    if (config.greeting !== prevGreeting.current) {
      prevGreeting.current = config.greeting;
      setMessages([{ role: 'bot', text: config.greeting }]);
    }
  }, [config.greeting]);

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

    // Try API, fall back to simulated
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map((m) => ({
            role: m.role === 'bot' ? 'assistant' : 'user',
            content: m.text,
          })),
        }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setTyping(false);
      setMessages((prev) => [...prev, { role: 'bot', text: data.response || 'Sorry, something went wrong.' }]);
    } catch {
      setTimeout(() => {
        const reply = SIMULATED_REPLIES[Math.floor(Math.random() * SIMULATED_REPLIES.length)];
        setTyping(false);
        setMessages((prev) => [...prev, { role: 'bot', text: reply }]);
      }, 600 + Math.random() * 600);
    }
  }, [input, messages, typing]);

  const posStyle = config.position === 'bottom-left'
    ? { left: 20, right: 'auto' }
    : { right: 20, left: 'auto' };

  return (
    <div className="widget-chat-frame" style={posStyle}>
      {/* Header */}
      <div className="widget-chat-header" style={{ background: config.color }}>
        <div className="widget-chat-avatar" style={{ background: 'rgba(255,255,255,0.25)' }}>
          {config.botName.charAt(0)}
        </div>
        <div>
          <div className="widget-chat-header-name">{config.botName}</div>
          <div className="widget-chat-header-status">
            <span className="widget-chat-online-dot" />
            Online
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="widget-chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`widget-chat-msg ${msg.role}`}>
            {msg.role === 'bot' && (
              <div className="widget-chat-msg-avatar" style={{ background: config.color }}>
                {config.botName.charAt(0)}
              </div>
            )}
            <div
              className="widget-chat-msg-bubble"
              style={msg.role === 'user' ? { background: config.color } : undefined}
            >
              {msg.text}
            </div>
          </div>
        ))}
        {typing && (
          <div className="widget-chat-msg bot">
            <div className="widget-chat-msg-avatar" style={{ background: config.color }}>
              {config.botName.charAt(0)}
            </div>
            <div className="widget-chat-msg-bubble">
              <span className="widget-typing-dots"><span /><span /><span /></span>
            </div>
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      {/* Input */}
      <div className="widget-chat-input-area">
        <input
          className="widget-chat-input"
          placeholder="Type a message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button
          className="widget-chat-send"
          onClick={sendMessage}
          style={{ background: config.color }}
        >
          {'\u27A4'}
        </button>
      </div>
    </div>
  );
}
