/**
 * AgentNexLiFy Embeddable Chat Widget v2.0.0
 * https://agentnexlify.com
 *
 * Pure JavaScript, zero dependencies, Shadow DOM isolated.
 * Designed to be served from CDN and embedded on third-party sites.
 *
 * Usage:
 *   <script src="https://cdn.agentnexlify.com/widget.js"
 *     data-key="YOUR_API_KEY"
 *     data-color="#00bfff"
 *     data-name="AI Assistant"
 *     data-position="bottom-right"
 *     data-greeting="Hi! How can we help you today?">
 *   </script>
 */
(function () {
  "use strict";

  // Prevent double-initialization
  if (window.__agentNexlifyWidget) return;
  window.__agentNexlifyWidget = true;

  // =========================================================================
  // 1. Script tag detection & base URL
  // =========================================================================
  var scriptTag =
    document.currentScript || document.querySelector("script[data-key]");

  var API_BASE = (function () {
    if (!scriptTag || !scriptTag.src) return "";
    // Derive API base from script src: https://example.com/widget.js -> https://example.com
    try {
      var url = new URL(scriptTag.src);
      return url.origin;
    } catch (e) {
      // Relative script — use current origin
      return window.location.origin;
    }
  })();

  function dataAttr(name, fallback) {
    if (scriptTag && scriptTag.hasAttribute("data-" + name)) {
      return scriptTag.getAttribute("data-" + name);
    }
    return fallback;
  }

  // Initial config from data attributes (overridden by server config later)
  var CONFIG = {
    apiKey: dataAttr("key", ""),
    primaryColor: dataAttr("color", "#00BFFF"),
    botName: dataAttr("name", "AI Assistant"),
    position: dataAttr("position", "bottom-right"),
    greeting: dataAttr("greeting", ""),
    showWatermark: true,
    collectName: true,
    collectEmail: true,
    collectPhone: true,
    businessPhone: "",
    allowedDomains: null,
  };

  // =========================================================================
  // 2. Utilities
  // =========================================================================
  function generateUUID() {
    // crypto.randomUUID where available, fallback to manual
    if (
      typeof crypto !== "undefined" &&
      typeof crypto.randomUUID === "function"
    ) {
      return crypto.randomUUID();
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
      /[xy]/g,
      function (c) {
        var r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      }
    );
  }

  function getSessionId() {
    var KEY = "anx_session_" + CONFIG.apiKey;
    var id;
    try {
      id = sessionStorage.getItem(KEY);
    } catch (e) {
      // sessionStorage unavailable
    }
    if (!id) {
      id = generateUUID();
      try {
        sessionStorage.setItem(KEY, id);
      } catch (e) {
        // ignore
      }
    }
    return id;
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // =========================================================================
  // 3. Network layer with retry and offline detection
  // =========================================================================
  var MAX_RETRIES = 2;
  var RETRY_DELAY_MS = 1500;

  function apiRequest(method, path, body, retries) {
    if (typeof retries === "undefined") retries = MAX_RETRIES;

    return new Promise(function (resolve, reject) {
      if (!navigator.onLine) {
        return reject({ offline: true, message: "You appear to be offline." });
      }

      var url = API_BASE + path;
      var xhr = new XMLHttpRequest();
      xhr.open(method, url, true);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.timeout = 30000;

      xhr.onload = function () {
        if (xhr.status === 429) {
          return reject({ rateLimited: true, status: 429 });
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            resolve(xhr.responseText);
          }
        } else {
          reject({ status: xhr.status, message: xhr.statusText });
        }
      };

      xhr.onerror = function () {
        if (retries > 0) {
          setTimeout(function () {
            apiRequest(method, path, body, retries - 1).then(resolve, reject);
          }, RETRY_DELAY_MS);
        } else {
          reject({ offline: !navigator.onLine, message: "Network error" });
        }
      };

      xhr.ontimeout = function () {
        if (retries > 0) {
          apiRequest(method, path, body, retries - 1).then(resolve, reject);
        } else {
          reject({ message: "Request timed out" });
        }
      };

      xhr.send(body ? JSON.stringify(body) : null);
    });
  }

  // =========================================================================
  // 4. CSS (injected into Shadow DOM — isolated from host page)
  // =========================================================================
  function buildCSS(pc, pos) {
    var isLeft = pos === "bottom-left";
    var side = isLeft ? "left" : "right";

    return [
      // Reset
      "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;",
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,Cantarell,sans-serif;}',

      // Floating button
      ".anx-btn{",
      "position:fixed;bottom:20px;" + side + ":20px;",
      "width:56px;height:56px;border-radius:50%;border:none;",
      "background:" + pc + ";cursor:pointer;z-index:2147483646;",
      "box-shadow:0 4px 14px rgba(0,0,0,.3);",
      "display:flex;align-items:center;justify-content:center;",
      "transition:transform .2s ease,box-shadow .2s ease;",
      "}",
      ".anx-btn:hover{transform:scale(1.08);box-shadow:0 6px 20px rgba(0,0,0,.4);}",
      ".anx-btn svg{width:26px;height:26px;fill:#fff;}",
      ".anx-btn.anx-hide{display:none;}",

      // Notification dot on button
      ".anx-dot{",
      "position:absolute;top:0;" + (isLeft ? "right" : "left") + ":0;",
      "width:14px;height:14px;border-radius:50%;",
      "background:#ef4444;border:2px solid #fff;",
      "display:none;",
      "}",
      ".anx-dot.anx-show{display:block;}",

      // Chat panel
      ".anx-panel{",
      "position:fixed;bottom:20px;" + side + ":20px;",
      "width:300px;height:calc(100vh - 40px);max-height:600px;",
      "background:#fff;border-radius:12px;",
      "box-shadow:0 8px 30px rgba(0,0,0,.2);",
      "display:flex;flex-direction:column;overflow:hidden;",
      "z-index:2147483647;",
      "transform:scale(0.92) translateY(10px);opacity:0;pointer-events:none;",
      "transition:transform .25s ease,opacity .25s ease;",
      "transform-origin:bottom " + side + ";",
      "}",
      ".anx-panel.anx-open{",
      "transform:scale(1) translateY(0);opacity:1;pointer-events:auto;",
      "}",

      // Header
      ".anx-header{",
      "display:flex;align-items:center;gap:10px;",
      "padding:14px 16px;",
      "background:" + pc + ";color:#fff;flex-shrink:0;",
      "}",
      ".anx-logo{",
      "width:36px;height:36px;border-radius:50%;",
      "background:rgba(255,255,255,.2);",
      "display:flex;align-items:center;justify-content:center;",
      "font-size:18px;font-weight:700;flex-shrink:0;",
      "}",
      ".anx-header-info{flex:1;min-width:0;}",
      ".anx-header-name{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}",
      ".anx-header-status{display:flex;align-items:center;gap:5px;font-size:11px;opacity:.85;}",
      ".anx-status-dot{width:6px;height:6px;border-radius:50%;background:#4ade80;flex-shrink:0;}",
      ".anx-close{",
      "background:none;border:none;color:#fff;cursor:pointer;",
      "font-size:20px;line-height:1;padding:4px;opacity:.7;",
      "transition:opacity .15s;",
      "}",
      ".anx-close:hover{opacity:1;}",

      // Messages area
      ".anx-messages{",
      "flex:1;overflow-y:auto;padding:14px;",
      "display:flex;flex-direction:column;gap:8px;",
      "background:#f9fafb;",
      "}",
      ".anx-messages::-webkit-scrollbar{width:4px;}",
      ".anx-messages::-webkit-scrollbar-thumb{background:#d1d5db;border-radius:4px;}",

      // Message bubbles
      ".anx-msg{",
      "max-width:85%;padding:9px 13px;border-radius:12px;",
      "font-size:13px;line-height:1.5;word-wrap:break-word;",
      "animation:anx-fade .2s ease;",
      "}",
      "@keyframes anx-fade{from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:none;}}",
      ".anx-msg-bot{",
      "align-self:flex-start;background:#fff;color:#1f2937;",
      "border:1px solid #e5e7eb;border-bottom-left-radius:3px;",
      "}",
      ".anx-msg-user{",
      "align-self:flex-end;background:" + pc + ";color:#fff;",
      "border-bottom-right-radius:3px;",
      "}",
      ".anx-msg-error{",
      "align-self:center;background:#fef2f2;color:#dc2626;",
      "border:1px solid #fecaca;font-size:12px;text-align:center;",
      "border-radius:8px;",
      "}",

      // Typing indicator
      ".anx-typing{display:flex;gap:4px;padding:9px 13px;align-self:flex-start;}",
      ".anx-typing span{",
      "width:6px;height:6px;border-radius:50%;background:#9ca3af;",
      "animation:anx-bounce .8s infinite;",
      "}",
      ".anx-typing span:nth-child(2){animation-delay:.1s;}",
      ".anx-typing span:nth-child(3){animation-delay:.2s;}",
      "@keyframes anx-bounce{0%,60%,100%{transform:translateY(0);}30%{transform:translateY(-4px);}}",

      // Input area
      ".anx-input-area{",
      "display:flex;align-items:center;gap:8px;",
      "padding:10px 12px;border-top:1px solid #e5e7eb;",
      "background:#fff;flex-shrink:0;",
      "}",
      ".anx-input{",
      "flex:1;padding:8px 12px;border:1px solid #d1d5db;",
      "border-radius:20px;font-size:13px;outline:none;",
      "color:#1f2937;background:#fff;",
      "transition:border-color .15s;",
      "}",
      ".anx-input::placeholder{color:#9ca3af;}",
      ".anx-input:focus{border-color:" + pc + ";}",
      ".anx-send{",
      "width:34px;height:34px;border:none;border-radius:50%;",
      "background:" + pc + ";cursor:pointer;flex-shrink:0;",
      "display:flex;align-items:center;justify-content:center;",
      "transition:opacity .15s;",
      "}",
      ".anx-send:disabled{opacity:.4;cursor:default;}",
      ".anx-send svg{width:16px;height:16px;fill:#fff;}",

      // Watermark
      ".anx-watermark{",
      "text-align:center;padding:5px;background:#fff;",
      "border-top:1px solid #f3f4f6;flex-shrink:0;",
      "}",
      ".anx-watermark a{",
      "color:#9ca3af;font-size:10px;text-decoration:none;",
      "}",
      ".anx-watermark a:hover{color:#6b7280;}",

      // Mobile: full screen
      "@media(max-width:500px){",
      ".anx-panel{",
      "top:0;left:0;right:0;bottom:0;width:100%;height:100%;max-height:100%;",
      "border-radius:0;transform:translateY(100%);opacity:1;",
      "transform-origin:bottom center;",
      "}",
      ".anx-panel.anx-open{transform:translateY(0);}",
      "}",
    ].join("\n");
  }

  // =========================================================================
  // 5. SVG icons
  // =========================================================================
  var ICON_CHAT =
    '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>';
  var ICON_CLOSE =
    '<svg viewBox="0 0 24 24"><path d="M19 6.4L17.6 5 12 10.6 6.4 5 5 6.4l5.6 5.6L5 17.6 6.4 19l5.6-5.6 5.6 5.6 1.4-1.4-5.6-5.6z"/></svg>';
  var ICON_SEND =
    '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';

  // =========================================================================
  // 6. Lead extraction from conversation
  // =========================================================================
  var extractedLead = { name: null, email: null, phone: null, submitted: {} };

  function tryExtractLead(text) {
    var changed = false;

    // Email
    if (!extractedLead.email) {
      var emailMatch = text.match(/[\w.+-]+@[\w-]+\.[\w.]+/);
      if (emailMatch) {
        extractedLead.email = emailMatch[0];
        changed = true;
      }
    }

    // Phone (US formats)
    if (!extractedLead.phone) {
      var phoneMatch = text.match(
        /(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/
      );
      if (phoneMatch) {
        extractedLead.phone = phoneMatch[0];
        changed = true;
      }
    }

    // Name (common patterns)
    if (!extractedLead.name) {
      var nameMatch = text.match(
        /(?:(?:i'm|im|i am|my name is|this is|call me)\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/i
      );
      if (nameMatch) {
        extractedLead.name = nameMatch[1];
        changed = true;
      }
    }

    if (changed) {
      submitLeadData();
    }
  }

  function submitLeadData() {
    var payload = {
      api_key: CONFIG.apiKey,
      session_id: getSessionId(),
      source: "widget",
      page_url: window.location.href,
    };

    // Only send fields not yet submitted
    var hasNew = false;
    if (extractedLead.name && !extractedLead.submitted.name) {
      payload.name = extractedLead.name;
      extractedLead.submitted.name = true;
      hasNew = true;
    }
    if (extractedLead.email && !extractedLead.submitted.email) {
      payload.email = extractedLead.email;
      extractedLead.submitted.email = true;
      hasNew = true;
    }
    if (extractedLead.phone && !extractedLead.submitted.phone) {
      payload.phone = extractedLead.phone;
      extractedLead.submitted.phone = true;
      hasNew = true;
    }

    if (hasNew) {
      apiRequest("POST", "/api/v1/widget/lead", payload).catch(function (err) {
        // Revert submitted flags so we retry next time
        if (payload.name) extractedLead.submitted.name = false;
        if (payload.email) extractedLead.submitted.email = false;
        if (payload.phone) extractedLead.submitted.phone = false;
      });
    }
  }

  // =========================================================================
  // 7. Widget class
  // =========================================================================
  function AgentNexlifyWidget() {
    this.isOpen = false;
    this.isTyping = false;
    this.messages = [];
    this.shadow = null;
    this.el = {};
    this.sessionId = getSessionId();
    this.rateLimited = false;
  }

  AgentNexlifyWidget.prototype.init = function () {
    var self = this;

    // Fetch server config, then merge with data-* overrides and render
    if (CONFIG.apiKey) {
      apiRequest("GET", "/api/v1/widget/config/" + CONFIG.apiKey)
        .then(function (serverCfg) {
          self.applyServerConfig(serverCfg);
          self.render();
        })
        .catch(function () {
          // Server unreachable — use data-* defaults
          self.render();
        });
    } else {
      // No API key — demo mode with defaults
      this.render();
    }
  };

  AgentNexlifyWidget.prototype.applyServerConfig = function (cfg) {
    // Server values are the base; data-* attributes override them
    if (cfg.bot_name && !scriptTag.hasAttribute("data-name")) {
      CONFIG.botName = cfg.bot_name;
    }
    if (cfg.primary_color && !scriptTag.hasAttribute("data-color")) {
      CONFIG.primaryColor = cfg.primary_color;
    }
    if (cfg.greeting_message && !scriptTag.hasAttribute("data-greeting")) {
      CONFIG.greeting = cfg.greeting_message;
    }
    if (cfg.position && !scriptTag.hasAttribute("data-position")) {
      CONFIG.position = cfg.position;
    }
    if (typeof cfg.show_watermark === "boolean") {
      CONFIG.showWatermark = cfg.show_watermark;
    }
    if (typeof cfg.collect_name === "boolean") {
      CONFIG.collectName = cfg.collect_name;
    }
    if (typeof cfg.collect_email === "boolean") {
      CONFIG.collectEmail = cfg.collect_email;
    }
    if (typeof cfg.collect_phone === "boolean") {
      CONFIG.collectPhone = cfg.collect_phone;
    }
    if (cfg.business_phone) {
      CONFIG.businessPhone = cfg.business_phone;
    }
    if (cfg.allowed_domains) {
      CONFIG.allowedDomains = cfg.allowed_domains;
    }
  };

  // =========================================================================
  // 8. Render
  // =========================================================================
  AgentNexlifyWidget.prototype.render = function () {
    // Domain whitelist check
    if (CONFIG.allowedDomains && CONFIG.allowedDomains.length > 0) {
      var currentHost = window.location.hostname;
      var allowed = CONFIG.allowedDomains.some(function (d) {
        return (
          currentHost === d ||
          currentHost.endsWith("." + d) ||
          d === "*"
        );
      });
      if (!allowed) return; // Silently refuse to render on unauthorized domains
    }

    // Create host element with shadow DOM
    var host = document.createElement("div");
    host.id = "agentnexlify-widget";
    document.body.appendChild(host);
    this.shadow = host.attachShadow({ mode: "closed" });

    // Inject CSS
    var style = document.createElement("style");
    style.textContent = buildCSS(CONFIG.primaryColor, CONFIG.position);
    this.shadow.appendChild(style);

    this.buildButton();
    this.buildPanel();

    // Greeting
    var greeting =
      CONFIG.greeting ||
      "Hi there! How can we help you today?";
    this.appendMessage("bot", greeting);

    // Listen for online/offline
    var self = this;
    window.addEventListener("online", function () {
      self.removeError();
    });
    window.addEventListener("offline", function () {
      self.showError("You appear to be offline. Messages will send when you reconnect.");
    });
  };

  // =========================================================================
  // 9. Build floating button
  // =========================================================================
  AgentNexlifyWidget.prototype.buildButton = function () {
    var self = this;

    var btn = document.createElement("button");
    btn.className = "anx-btn";
    btn.setAttribute("aria-label", "Open chat");
    btn.innerHTML = ICON_CHAT;

    var dot = document.createElement("span");
    dot.className = "anx-dot";
    btn.appendChild(dot);

    btn.addEventListener("click", function () {
      self.toggle();
    });

    this.shadow.appendChild(btn);
    this.el.btn = btn;
    this.el.dot = dot;
  };

  // =========================================================================
  // 10. Build chat panel
  // =========================================================================
  AgentNexlifyWidget.prototype.buildPanel = function () {
    var self = this;

    // Panel container
    var panel = document.createElement("div");
    panel.className = "anx-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Chat with " + CONFIG.botName);

    // --- Header ---
    var header = document.createElement("div");
    header.className = "anx-header";

    var logo = document.createElement("div");
    logo.className = "anx-logo";
    logo.textContent = CONFIG.botName.charAt(0).toUpperCase();

    var info = document.createElement("div");
    info.className = "anx-header-info";

    var name = document.createElement("div");
    name.className = "anx-header-name";
    name.textContent = CONFIG.botName;

    var status = document.createElement("div");
    status.className = "anx-header-status";
    var statusDot = document.createElement("span");
    statusDot.className = "anx-status-dot";
    status.appendChild(statusDot);
    status.appendChild(document.createTextNode("Online"));

    info.appendChild(name);
    info.appendChild(status);

    var closeBtn = document.createElement("button");
    closeBtn.className = "anx-close";
    closeBtn.setAttribute("aria-label", "Close chat");
    closeBtn.innerHTML = "&times;";
    closeBtn.addEventListener("click", function () {
      self.close();
    });

    header.appendChild(logo);
    header.appendChild(info);
    header.appendChild(closeBtn);

    // --- Messages ---
    var messages = document.createElement("div");
    messages.className = "anx-messages";
    messages.setAttribute("role", "log");
    messages.setAttribute("aria-live", "polite");

    // --- Input area ---
    var inputArea = document.createElement("div");
    inputArea.className = "anx-input-area";

    var input = document.createElement("input");
    input.className = "anx-input";
    input.type = "text";
    input.placeholder = "Type a message...";
    input.setAttribute("aria-label", "Type a message");
    input.autocomplete = "off";

    var sendBtn = document.createElement("button");
    sendBtn.className = "anx-send";
    sendBtn.innerHTML = ICON_SEND;
    sendBtn.disabled = true;
    sendBtn.setAttribute("aria-label", "Send message");

    input.addEventListener("input", function () {
      sendBtn.disabled = !input.value.trim();
    });

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && input.value.trim() && !self.isTyping) {
        self.handleSend();
      }
    });

    sendBtn.addEventListener("click", function () {
      if (input.value.trim() && !self.isTyping) {
        self.handleSend();
      }
    });

    inputArea.appendChild(input);
    inputArea.appendChild(sendBtn);

    // --- Watermark ---
    var watermark = document.createElement("div");
    watermark.className = "anx-watermark";
    if (CONFIG.showWatermark) {
      var wLink = document.createElement("a");
      wLink.href = "https://agentnexlify.com";
      wLink.target = "_blank";
      wLink.rel = "noopener noreferrer";
      wLink.textContent = "Powered by AgentNexLiFy";
      watermark.appendChild(wLink);
    }

    // --- Assemble ---
    panel.appendChild(header);
    panel.appendChild(messages);
    panel.appendChild(inputArea);
    if (CONFIG.showWatermark) {
      panel.appendChild(watermark);
    }

    this.shadow.appendChild(panel);
    this.el.panel = panel;
    this.el.messages = messages;
    this.el.input = input;
    this.el.sendBtn = sendBtn;
  };

  // =========================================================================
  // 11. Open / Close / Toggle
  // =========================================================================
  AgentNexlifyWidget.prototype.open = function () {
    this.isOpen = true;
    this.el.panel.classList.add("anx-open");
    this.el.btn.classList.add("anx-hide");
    this.el.dot.classList.remove("anx-show");
    this.el.input.focus();
    this.scrollToBottom();
  };

  AgentNexlifyWidget.prototype.close = function () {
    this.isOpen = false;
    this.el.panel.classList.remove("anx-open");
    this.el.btn.classList.remove("anx-hide");
  };

  AgentNexlifyWidget.prototype.toggle = function () {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  };

  // =========================================================================
  // 12. Message rendering
  // =========================================================================
  AgentNexlifyWidget.prototype.appendMessage = function (role, text) {
    var div = document.createElement("div");
    div.className = "anx-msg " + (role === "user" ? "anx-msg-user" : "anx-msg-bot");
    div.textContent = text;
    this.el.messages.appendChild(div);
    this.messages.push({ role: role, text: text });
    this.scrollToBottom();
  };

  AgentNexlifyWidget.prototype.showError = function (text) {
    this.removeError();
    var div = document.createElement("div");
    div.className = "anx-msg anx-msg-error";
    div.setAttribute("data-error", "1");
    div.textContent = text;
    this.el.messages.appendChild(div);
    this.scrollToBottom();
  };

  AgentNexlifyWidget.prototype.removeError = function () {
    var errs = this.el.messages
      ? this.el.messages.querySelectorAll("[data-error]")
      : [];
    for (var i = 0; i < errs.length; i++) {
      errs[i].parentNode.removeChild(errs[i]);
    }
  };

  AgentNexlifyWidget.prototype.showTyping = function () {
    if (this.isTyping) return;
    this.isTyping = true;
    var div = document.createElement("div");
    div.className = "anx-typing";
    div.setAttribute("data-typing", "1");
    div.innerHTML = "<span></span><span></span><span></span>";
    this.el.messages.appendChild(div);
    this.scrollToBottom();
  };

  AgentNexlifyWidget.prototype.hideTyping = function () {
    this.isTyping = false;
    var els = this.el.messages.querySelectorAll("[data-typing]");
    for (var i = 0; i < els.length; i++) {
      els[i].parentNode.removeChild(els[i]);
    }
  };

  AgentNexlifyWidget.prototype.scrollToBottom = function () {
    var m = this.el.messages;
    requestAnimationFrame(function () {
      m.scrollTop = m.scrollHeight;
    });
  };

  // =========================================================================
  // 13. Send message
  // =========================================================================
  AgentNexlifyWidget.prototype.handleSend = function () {
    var text = this.el.input.value.trim();
    if (!text || this.isTyping) return;

    this.el.input.value = "";
    this.el.sendBtn.disabled = true;
    this.removeError();
    this.appendMessage("user", text);

    // Extract lead info from user message
    tryExtractLead(text);

    // Send to API
    this.showTyping();
    var self = this;

    if (!CONFIG.apiKey) {
      // No API key — can't send to backend
      setTimeout(function () {
        self.hideTyping();
        self.appendMessage(
          "bot",
          "Thanks for your message! Our team will follow up with you shortly."
        );
      }, 600);
      return;
    }

    apiRequest("POST", "/api/v1/widget/chat", {
      api_key: CONFIG.apiKey,
      session_id: self.sessionId,
      message: text,
    })
      .then(function (data) {
        self.hideTyping();
        var reply =
          data.reply ||
          data.response ||
          "Thanks for your message!";
        self.appendMessage("bot", reply);

        // Also extract lead info from bot response context
        // (the bot may echo back contact info the user provided)
        if (!self.isOpen) {
          self.el.dot.classList.add("anx-show");
        }
      })
      .catch(function (err) {
        self.hideTyping();

        if (err.rateLimited) {
          self.rateLimited = true;
          var msg = CONFIG.businessPhone
            ? "Our chat is temporarily busy. Call us at " +
              CONFIG.businessPhone +
              " for immediate help."
            : "Our chat is temporarily busy. Please try again in a few minutes.";
          self.showError(msg);
        } else if (err.offline) {
          self.showError(
            "You appear to be offline. Your message will send when you reconnect."
          );
        } else {
          self.showError(
            "Something went wrong. Please try again."
          );
        }
      });
  };

  // =========================================================================
  // 14. Boot
  // =========================================================================
  function boot() {
    var widget = new AgentNexlifyWidget();
    widget.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
