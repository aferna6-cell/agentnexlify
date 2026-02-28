/**
 * AgentNexLiFy Chat Widget v1.0.0
 * https://agentnexlify.com
 *
 * Embeddable AI chat widget for businesses.
 * Vanilla JS, zero dependencies, Shadow DOM isolated.
 *
 * Usage:
 *   <script src="https://agentnexlify.com/widget/nexlify-chat.js"
 *     data-business-id="YOUR_ID"
 *     data-business-name="Your Business"
 *     data-primary-color="#00bfff"
 *     data-position="right"
 *     data-greeting="Hi! How can we help?"
 *     data-webhook-url="https://your-api.com/leads">
 *   </script>
 */
(function () {
  "use strict";

  // Prevent double-init
  if (window.__nexlifyWidgetLoaded) return;
  window.__nexlifyWidgetLoaded = true;

  // ---------------------------------------------------------------------------
  // 1. Configuration from script tag data attributes
  // ---------------------------------------------------------------------------
  var scriptTag =
    document.currentScript ||
    document.querySelector('script[data-business-id]');

  var CONFIG = {
    businessId: attr("data-business-id", "demo"),
    businessName: attr("data-business-name", "Us"),
    primaryColor: attr("data-primary-color", "#00bfff"),
    position: attr("data-position", "right"),
    greeting: attr(
      "data-greeting",
      "Hi there! \uD83D\uDC4B How can I help you today?"
    ),
    webhookUrl: attr("data-webhook-url", ""),
  };

  function attr(name, fallback) {
    return scriptTag && scriptTag.getAttribute(name)
      ? scriptTag.getAttribute(name)
      : fallback;
  }

  // ---------------------------------------------------------------------------
  // 2. Session storage helpers
  // ---------------------------------------------------------------------------
  var STORAGE_KEY = "nexlify_chat_" + CONFIG.businessId;
  var LEADS_KEY = "nexlify_leads_" + CONFIG.businessId;

  function loadSession() {
    try {
      var raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveSession(messages, leadState) {
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ messages: messages, leadState: leadState })
      );
    } catch (e) {
      // Storage full or unavailable — fail silently
    }
  }

  function storeLeadLocally(lead) {
    try {
      var existing = JSON.parse(localStorage.getItem(LEADS_KEY) || "[]");
      existing.push(lead);
      localStorage.setItem(LEADS_KEY, JSON.stringify(existing));
    } catch (e) {
      // fail silently
    }
  }

  // ---------------------------------------------------------------------------
  // 3. CSS (injected into Shadow DOM)
  // ---------------------------------------------------------------------------
  function buildCSS() {
    var pc = CONFIG.primaryColor;
    var pos = CONFIG.position === "left" ? "left" : "right";
    var oppositePos = pos === "left" ? "right" : "left";

    return (
      /* Reset inside shadow */ '\
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,sans-serif;}\
\
/* ---- Bubble ---- */\
.nex-bubble{\
  position:fixed;bottom:24px;' +
      pos +
      ':24px;\
  width:60px;height:60px;border-radius:50%;\
  background:' +
      pc +
      ';\
  display:flex;align-items:center;justify-content:center;\
  cursor:pointer;z-index:2147483646;\
  box-shadow:0 4px 16px rgba(0,0,0,.3);\
  transition:transform .25s ease,box-shadow .25s ease;\
}\
.nex-bubble:hover{transform:scale(1.08);box-shadow:0 6px 24px rgba(0,0,0,.4);}\
.nex-bubble svg{width:28px;height:28px;fill:#fff;}\
.nex-bubble.nex-hidden{display:none;}\
\
/* Unread badge */\
.nex-badge{\
  position:absolute;top:-2px;' +
      oppositePos +
      ':-2px;\
  background:#ff4757;color:#fff;font-size:11px;font-weight:700;\
  width:20px;height:20px;border-radius:50%;\
  display:flex;align-items:center;justify-content:center;\
  opacity:0;transition:opacity .2s;\
}\
.nex-badge.nex-show{opacity:1;}\
\
/* ---- Chat Window ---- */\
.nex-window{\
  position:fixed;bottom:96px;' +
      pos +
      ':24px;\
  width:380px;height:520px;\
  background:#1a1a2e;\
  border-radius:16px;\
  box-shadow:0 8px 40px rgba(0,0,0,.45);\
  display:flex;flex-direction:column;\
  overflow:hidden;z-index:2147483647;\
  transform:translateY(20px);opacity:0;\
  pointer-events:none;\
  transition:transform .3s ease,opacity .3s ease;\
}\
.nex-window.nex-open{\
  transform:translateY(0);opacity:1;pointer-events:auto;\
}\
\
/* ---- Header ---- */\
.nex-header{\
  display:flex;align-items:center;justify-content:space-between;\
  padding:14px 16px;\
  background:#16213e;\
  color:#fff;font-size:15px;font-weight:600;\
  flex-shrink:0;\
}\
.nex-header-left{display:flex;align-items:center;gap:8px;}\
.nex-header-dot{width:8px;height:8px;border-radius:50%;background:#2ecc71;flex-shrink:0;}\
.nex-header-btns{display:flex;gap:6px;}\
.nex-header-btn{\
  width:28px;height:28px;border:none;border-radius:6px;\
  background:rgba(255,255,255,.1);color:#fff;cursor:pointer;\
  display:flex;align-items:center;justify-content:center;\
  font-size:16px;transition:background .15s;\
}\
.nex-header-btn:hover{background:rgba(255,255,255,.2);}\
\
/* ---- Messages ---- */\
.nex-messages{\
  flex:1;overflow-y:auto;padding:16px;\
  display:flex;flex-direction:column;gap:10px;\
  scrollbar-width:thin;\
  scrollbar-color:rgba(255,255,255,.15) transparent;\
}\
.nex-messages::-webkit-scrollbar{width:5px;}\
.nex-messages::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:4px;}\
\
.nex-msg{\
  max-width:82%;padding:10px 14px;border-radius:14px;\
  font-size:14px;line-height:1.5;color:#fff;\
  word-wrap:break-word;animation:nex-fadeIn .25s ease;\
}\
@keyframes nex-fadeIn{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}\
\
.nex-msg-bot{\
  align-self:flex-start;background:#2a2a3e;\
  border-bottom-left-radius:4px;\
}\
.nex-msg-user{\
  align-self:flex-end;background:' +
      pc +
      ';\
  border-bottom-right-radius:4px;\
}\
\
/* Typing indicator */\
.nex-typing{display:flex;gap:4px;padding:10px 14px;align-self:flex-start;}\
.nex-typing span{\
  width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.4);\
  animation:nex-dot .9s infinite;\
}\
.nex-typing span:nth-child(2){animation-delay:.15s;}\
.nex-typing span:nth-child(3){animation-delay:.3s;}\
@keyframes nex-dot{0%,60%,100%{opacity:.3;transform:translateY(0);}30%{opacity:1;transform:translateY(-4px);}}\
\
/* ---- Input ---- */\
.nex-input-area{\
  display:flex;align-items:center;gap:8px;padding:12px 14px;\
  background:#16213e;flex-shrink:0;\
}\
.nex-input{\
  flex:1;padding:10px 14px;border:1px solid rgba(255,255,255,.12);\
  border-radius:22px;background:#1a1a2e;color:#fff;\
  font-size:14px;outline:none;transition:border-color .2s;\
}\
.nex-input::placeholder{color:rgba(255,255,255,.4);}\
.nex-input:focus{border-color:' +
      pc +
      ';}\
.nex-send{\
  width:38px;height:38px;border:none;border-radius:50%;\
  background:' +
      pc +
      ';cursor:pointer;\
  display:flex;align-items:center;justify-content:center;\
  transition:opacity .15s;\
  flex-shrink:0;\
}\
.nex-send:disabled{opacity:.4;cursor:default;}\
.nex-send svg{width:18px;height:18px;fill:#fff;}\
\
/* ---- Watermark ---- */\
.nex-watermark{\
  text-align:center;padding:6px;background:#16213e;\
  flex-shrink:0;\
}\
.nex-watermark a{\
  color:rgba(255,255,255,.35);font-size:11px;text-decoration:none;\
}\
.nex-watermark a:hover{color:rgba(255,255,255,.55);}\
\
/* ---- Mobile fullscreen ---- */\
@media(max-width:768px){\
  .nex-window{\
    top:0;left:0;right:0;bottom:0;width:100%;height:100%;\
    border-radius:0;transform:translateY(100%);opacity:1;\
  }\
  .nex-window.nex-open{transform:translateY(0);}\
  .nex-bubble{bottom:16px;' +
      pos +
      ':16px;}\
}\
'
    );
  }

  // ---------------------------------------------------------------------------
  // 4. HTML templates
  // ---------------------------------------------------------------------------
  var SVG_CHAT =
    '<svg viewBox="0 0 24 24"><path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2zm0 14H5.17L4 17.17V4h16v12z"/><path d="M7 9h10v2H7zm0-3h10v2H7z"/></svg>';

  var SVG_SEND =
    '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';

  // ---------------------------------------------------------------------------
  // 5. Keyword-based response engine (DEMO MODE)
  // ---------------------------------------------------------------------------
  var messageCount = 0;
  var leadState = {
    capturing: false,
    step: 0, // 0=name, 1=email, 2=phone
    name: "",
    email: "",
    phone: "",
    captured: false,
  };

  var PATTERNS = [
    {
      keys: ["hi", "hello", "hey", "howdy", "hola", "sup", "good morning", "good afternoon", "good evening"],
      response: function () {
        return (
          "Hi there! \uD83D\uDC4B Welcome to " +
          CONFIG.businessName +
          ". How can I help you today?"
        );
      },
    },
    {
      keys: ["price", "cost", "how much", "quote", "pricing", "rate", "fee", "estimate", "budget"],
      response: function () {
        return "I'd be happy to help with pricing! Could you tell me a bit about what you're looking for? I'll connect you with our team for a personalized quote.";
      },
    },
    {
      keys: ["hours", "open", "available", "schedule", "appointment", "when", "time"],
      response: function () {
        return "We're typically available Monday\u2013Friday 8am\u20136pm. Would you like to schedule an appointment?";
      },
    },
    {
      keys: ["service", "what do you do", "help with", "offer", "provide", "specialize"],
      response: function () {
        return (
          "We offer a full range of services to meet your needs. What specific area can I help you with?"
        );
      },
    },
    {
      keys: ["location", "address", "where", "directions", "find you"],
      response: function () {
        return "Great question! You can find our location details on our website. Would you like me to have someone reach out with directions?";
      },
    },
    {
      keys: ["phone", "call", "contact", "reach", "number"],
      response: function () {
        return "You can reach our team directly through this chat, or I can have someone call you back. Would you like that?";
      },
    },
    {
      keys: ["thank", "thanks", "appreciate"],
      response: function () {
        return "You're welcome! \uD83D\uDE0A Is there anything else I can help with?";
      },
    },
    {
      keys: ["bye", "goodbye", "see you", "later"],
      response: function () {
        return "Thanks for chatting with us! Have a great day. Feel free to come back anytime! \uD83D\uDC4B";
      },
    },
  ];

  function generateResponse(userText) {
    var text = userText.toLowerCase().trim();
    messageCount++;

    // If we're in lead-capture mode, handle that flow
    if (leadState.capturing) {
      return handleLeadCapture(text, userText);
    }

    // After 2+ user messages, trigger lead capture
    if (messageCount >= 2 && !leadState.captured) {
      leadState.capturing = true;
      leadState.step = 0;
      return "I'd love to help you further! Could I get your name so our team can follow up with you personally?";
    }

    // Keyword matching
    for (var i = 0; i < PATTERNS.length; i++) {
      for (var k = 0; k < PATTERNS[i].keys.length; k++) {
        if (text.indexOf(PATTERNS[i].keys[k]) !== -1) {
          return PATTERNS[i].response();
        }
      }
    }

    // Fallback
    return "That's a great question! Let me connect you with our team who can help with that specifically. In the meantime, is there anything else I can assist with?";
  }

  function handleLeadCapture(lowerText, originalText) {
    switch (leadState.step) {
      case 0:
        leadState.name = originalText.trim();
        leadState.step = 1;
        return (
          "Nice to meet you, " +
          leadState.name +
          "! What's the best email address to reach you at?"
        );
      case 1:
        leadState.email = originalText.trim();
        leadState.step = 2;
        return "Got it! And a phone number where our team can reach you? (or type \"skip\" to skip)";
      case 2:
        leadState.phone =
          lowerText === "skip" ? "" : originalText.trim();
        leadState.capturing = false;
        leadState.captured = true;
        submitLead();
        var contact = leadState.email;
        return (
          "Thanks, " +
          leadState.name +
          "! \uD83C\uDF89 Our team will reach out to you at " +
          contact +
          " shortly. Is there anything else I can help with?"
        );
      default:
        leadState.capturing = false;
        return "Thanks for the info! How else can I help?";
    }
  }

  function submitLead() {
    var lead = {
      businessId: CONFIG.businessId,
      name: leadState.name,
      email: leadState.email,
      phone: leadState.phone,
      timestamp: new Date().toISOString(),
      source: window.location.href,
    };

    // Console log for demo
    console.log("[AgentNexLiFy] Lead captured:", lead);

    // Webhook POST
    if (CONFIG.webhookUrl) {
      try {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", CONFIG.webhookUrl, true);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.send(JSON.stringify(lead));
      } catch (e) {
        console.warn("[AgentNexLiFy] Webhook POST failed:", e);
      }
    }

    // Local storage fallback
    storeLeadLocally(lead);
  }

  // ---------------------------------------------------------------------------
  // 6. Widget class
  // ---------------------------------------------------------------------------
  function NexlifyChat() {
    this.isOpen = false;
    this.messages = [];
    this.host = null;
    this.shadow = null;
    this.els = {};
    this.unread = 0;
    this.init();
  }

  NexlifyChat.prototype.init = function () {
    // Restore session
    var session = loadSession();
    if (session) {
      this.messages = session.messages || [];
      if (session.leadState) {
        Object.keys(session.leadState).forEach(function (k) {
          leadState[k] = session.leadState[k];
        });
        // Restore messageCount from messages
        messageCount = this.messages.filter(function (m) {
          return m.sender === "user";
        }).length;
      }
    }

    // Create host element
    this.host = document.createElement("div");
    this.host.id = "nexlify-chat-widget";
    document.body.appendChild(this.host);

    // Attach shadow DOM
    this.shadow = this.host.attachShadow({ mode: "closed" });

    // Inject styles
    var style = document.createElement("style");
    style.textContent = buildCSS();
    this.shadow.appendChild(style);

    // Build DOM
    this.buildBubble();
    this.buildWindow();

    // Render restored messages
    if (this.messages.length === 0) {
      this.addBotMessage(CONFIG.greeting);
    } else {
      var self = this;
      this.messages.forEach(function (m) {
        self.renderMessage(m.text, m.sender === "user");
      });
    }
  };

  NexlifyChat.prototype.buildBubble = function () {
    var self = this;
    var bubble = document.createElement("div");
    bubble.className = "nex-bubble";
    bubble.innerHTML = SVG_CHAT;
    bubble.setAttribute("aria-label", "Open chat");
    bubble.setAttribute("role", "button");
    bubble.setAttribute("tabindex", "0");

    var badge = document.createElement("span");
    badge.className = "nex-badge";
    badge.textContent = "1";
    bubble.appendChild(badge);

    bubble.addEventListener("click", function () {
      self.toggle();
    });
    bubble.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        self.toggle();
      }
    });

    this.shadow.appendChild(bubble);
    this.els.bubble = bubble;
    this.els.badge = badge;
  };

  NexlifyChat.prototype.buildWindow = function () {
    var self = this;
    var win = document.createElement("div");
    win.className = "nex-window";
    win.setAttribute("role", "dialog");
    win.setAttribute("aria-label", "Chat window");

    // Header
    var header = document.createElement("div");
    header.className = "nex-header";

    var headerLeft = document.createElement("div");
    headerLeft.className = "nex-header-left";

    var dot = document.createElement("span");
    dot.className = "nex-header-dot";
    headerLeft.appendChild(dot);

    var title = document.createElement("span");
    title.textContent =
      "Chat with " + CONFIG.businessName + " \uD83E\uDD16";
    headerLeft.appendChild(title);

    var headerBtns = document.createElement("div");
    headerBtns.className = "nex-header-btns";

    var minBtn = document.createElement("button");
    minBtn.className = "nex-header-btn";
    minBtn.innerHTML = "\u2013";
    minBtn.title = "Minimize";
    minBtn.setAttribute("aria-label", "Minimize chat");
    minBtn.addEventListener("click", function () {
      self.close();
    });

    var closeBtn = document.createElement("button");
    closeBtn.className = "nex-header-btn";
    closeBtn.innerHTML = "\u2715";
    closeBtn.title = "Close";
    closeBtn.setAttribute("aria-label", "Close chat");
    closeBtn.addEventListener("click", function () {
      self.close();
    });

    headerBtns.appendChild(minBtn);
    headerBtns.appendChild(closeBtn);

    header.appendChild(headerLeft);
    header.appendChild(headerBtns);

    // Messages container
    var msgs = document.createElement("div");
    msgs.className = "nex-messages";
    msgs.setAttribute("role", "log");
    msgs.setAttribute("aria-live", "polite");

    // Input area
    var inputArea = document.createElement("div");
    inputArea.className = "nex-input-area";

    var input = document.createElement("input");
    input.className = "nex-input";
    input.type = "text";
    input.placeholder = "Type a message\u2026";
    input.setAttribute("aria-label", "Message input");
    input.autocomplete = "off";

    var sendBtn = document.createElement("button");
    sendBtn.className = "nex-send";
    sendBtn.innerHTML = SVG_SEND;
    sendBtn.disabled = true;
    sendBtn.setAttribute("aria-label", "Send message");

    input.addEventListener("input", function () {
      sendBtn.disabled = !input.value.trim();
    });

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && input.value.trim()) {
        self.sendMessage(input.value.trim());
        input.value = "";
        sendBtn.disabled = true;
      }
    });

    sendBtn.addEventListener("click", function () {
      if (input.value.trim()) {
        self.sendMessage(input.value.trim());
        input.value = "";
        sendBtn.disabled = true;
      }
    });

    inputArea.appendChild(input);
    inputArea.appendChild(sendBtn);

    // Watermark
    var watermark = document.createElement("div");
    watermark.className = "nex-watermark";
    var wLink = document.createElement("a");
    wLink.href = "https://agentnexlify.com/free-widget";
    wLink.target = "_blank";
    wLink.rel = "noopener noreferrer";
    wLink.textContent = "Powered by AgentNexLiFy";
    watermark.appendChild(wLink);

    // Assemble
    win.appendChild(header);
    win.appendChild(msgs);
    win.appendChild(inputArea);
    win.appendChild(watermark);
    this.shadow.appendChild(win);

    this.els.window = win;
    this.els.messages = msgs;
    this.els.input = input;
    this.els.sendBtn = sendBtn;
  };

  // ---------------------------------------------------------------------------
  // 7. Message handling
  // ---------------------------------------------------------------------------
  NexlifyChat.prototype.renderMessage = function (text, isUser) {
    var div = document.createElement("div");
    div.className = "nex-msg " + (isUser ? "nex-msg-user" : "nex-msg-bot");
    div.textContent = text;
    this.els.messages.appendChild(div);
    this.scrollToBottom();
  };

  NexlifyChat.prototype.addBotMessage = function (text) {
    this.messages.push({ sender: "bot", text: text });
    this.renderMessage(text, false);
    this.persist();
    if (!this.isOpen) {
      this.unread++;
      this.els.badge.textContent = this.unread;
      this.els.badge.classList.add("nex-show");
    }
  };

  NexlifyChat.prototype.sendMessage = function (text) {
    // Render user message
    this.messages.push({ sender: "user", text: text });
    this.renderMessage(text, true);
    this.persist();

    // Show typing indicator
    var self = this;
    var typing = document.createElement("div");
    typing.className = "nex-typing";
    typing.innerHTML = "<span></span><span></span><span></span>";
    this.els.messages.appendChild(typing);
    this.scrollToBottom();

    // Simulate response delay (400-1200ms)
    var delay = 400 + Math.random() * 800;
    setTimeout(function () {
      if (typing.parentNode) typing.parentNode.removeChild(typing);
      var response = generateResponse(text);
      self.addBotMessage(response);
    }, delay);
  };

  NexlifyChat.prototype.scrollToBottom = function () {
    var msgs = this.els.messages;
    // Use requestAnimationFrame for reliable scroll after render
    requestAnimationFrame(function () {
      msgs.scrollTop = msgs.scrollHeight;
    });
  };

  NexlifyChat.prototype.persist = function () {
    saveSession(this.messages, leadState);
  };

  // ---------------------------------------------------------------------------
  // 8. Open / Close / Toggle
  // ---------------------------------------------------------------------------
  NexlifyChat.prototype.open = function () {
    this.isOpen = true;
    this.els.window.classList.add("nex-open");
    this.unread = 0;
    this.els.badge.classList.remove("nex-show");
    this.els.input.focus();
    this.scrollToBottom();
  };

  NexlifyChat.prototype.close = function () {
    this.isOpen = false;
    this.els.window.classList.remove("nex-open");
  };

  NexlifyChat.prototype.toggle = function () {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  };

  // ---------------------------------------------------------------------------
  // 9. Boot
  // ---------------------------------------------------------------------------
  function boot() {
    new NexlifyChat();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
