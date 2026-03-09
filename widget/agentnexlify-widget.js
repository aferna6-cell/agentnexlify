(function () {
  "use strict";

  // --- Double-init guard ---
  if (window.__agentNexlifyWidget) return;
  window.__agentNexlifyWidget = true;

  // --- Configuration ---
  const scriptTag = document.currentScript;
  const API_KEY = scriptTag?.getAttribute("data-api-key") || "";
  const BRAND_COLOR =
    scriptTag?.getAttribute("data-brand-color") || "#6cff5c";
  const API_BASE =
    scriptTag?.getAttribute("data-api-base") ||
    scriptTag?.src?.replace(/\/widget\/agentnexlify-widget\.js.*$/, "") ||
    "";

  const SESSION_KEY = "anx_session_id";
  const SESSION_TS_KEY = "anx_session_ts";
  const STATE_KEY = "anx_widget_state";
  const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

  // --- Session Management ---
  function _newSessionId() {
    return (
      "web_" +
      Date.now().toString(36) +
      "_" +
      Math.random().toString(36).slice(2, 10)
    );
  }

  function getSessionId() {
    let sid = localStorage.getItem(SESSION_KEY);
    const ts = parseInt(localStorage.getItem(SESSION_TS_KEY) || "0", 10);

    // Start a new session if none exists or last message was >30 min ago
    if (!sid || (ts && Date.now() - ts > SESSION_TIMEOUT_MS)) {
      sid = _newSessionId();
      localStorage.setItem(SESSION_KEY, sid);
    }

    // Update activity timestamp on every call
    localStorage.setItem(SESSION_TS_KEY, String(Date.now()));
    return sid;
  }

  function resetSession() {
    const sid = _newSessionId();
    localStorage.setItem(SESSION_KEY, sid);
    localStorage.setItem(SESSION_TS_KEY, String(Date.now()));
    // Clear chat UI
    const container = document.getElementById("anx-messages");
    if (container) container.innerHTML = "";
    return sid;
  }

  // --- Styles ---
  function injectStyles() {
    if (document.getElementById("anx-styles")) return;
    const style = document.createElement("style");
    style.id = "anx-styles";
    style.textContent = `
      #anx-container * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }

      #anx-bubble {
        position: fixed;
        bottom: 24px;
        right: 24px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: ${BRAND_COLOR};
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3);
        z-index: 99998;
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s;
        animation: anx-pulse 2s infinite;
      }

      #anx-bubble:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 32px rgba(0,0,0,0.4);
      }

      #anx-bubble.hidden {
        transform: scale(0);
        pointer-events: none;
      }

      #anx-bubble svg {
        width: 28px;
        height: 28px;
        fill: #fff;
      }

      #anx-badge {
        position: absolute;
        top: -2px;
        right: -2px;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #ff4444;
        color: white;
        font-size: 11px;
        font-weight: 700;
        display: none;
        align-items: center;
        justify-content: center;
      }

      @keyframes anx-pulse {
        0%, 100% { box-shadow: 0 4px 24px rgba(0,0,0,0.3); }
        50% { box-shadow: 0 4px 24px rgba(108,255,92,0.4); }
      }

      #anx-window {
        position: fixed;
        bottom: 24px;
        right: 24px;
        width: 380px;
        height: 560px;
        background: #0a0a0f;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        z-index: 99999;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        transform: scale(0.9) translateY(20px);
        opacity: 0;
        pointer-events: none;
        transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.25s;
      }

      #anx-window.open {
        transform: scale(1) translateY(0);
        opacity: 1;
        pointer-events: all;
      }

      #anx-header {
        background: linear-gradient(135deg, #111118, #16161f);
        padding: 16px 16px 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        flex-shrink: 0;
      }

      #anx-header-info {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      #anx-header-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: ${BRAND_COLOR};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: 700;
        color: #0a0a0f;
        flex-shrink: 0;
      }

      #anx-header-text h3 {
        color: #fff;
        font-size: 14px;
        font-weight: 600;
        line-height: 1.2;
      }

      #anx-header-text p {
        color: rgba(255,255,255,0.45);
        font-size: 11px;
        line-height: 1.3;
      }

      .anx-header-status {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: ${BRAND_COLOR};
        margin-right: 4px;
        vertical-align: middle;
      }

      #anx-header-actions {
        display: flex;
        gap: 4px;
      }

      #anx-header-actions button {
        width: 30px;
        height: 30px;
        border: none;
        background: rgba(255,255,255,0.06);
        border-radius: 8px;
        cursor: pointer;
        color: rgba(255,255,255,0.5);
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s, color 0.2s;
      }

      #anx-header-actions button:hover {
        background: rgba(255,255,255,0.12);
        color: #fff;
      }

      #anx-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.1) transparent;
      }

      #anx-messages::-webkit-scrollbar {
        width: 4px;
      }

      #anx-messages::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.1);
        border-radius: 4px;
      }

      .anx-msg {
        max-width: 85%;
        padding: 10px 14px;
        border-radius: 14px;
        font-size: 13.5px;
        line-height: 1.45;
        word-wrap: break-word;
        animation: anx-msgIn 0.3s ease-out;
      }

      @keyframes anx-msgIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
      }

      .anx-msg.assistant {
        background: #1a1a25;
        color: #e0e0e5;
        align-self: flex-start;
        border-bottom-left-radius: 4px;
      }

      .anx-msg.user {
        background: ${BRAND_COLOR};
        color: #0a0a0f;
        align-self: flex-end;
        border-bottom-right-radius: 4px;
        font-weight: 500;
      }

      .anx-typing {
        align-self: flex-start;
        display: flex;
        gap: 5px;
        padding: 12px 16px;
        background: #1a1a25;
        border-radius: 14px;
        border-bottom-left-radius: 4px;
      }

      .anx-typing span {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: rgba(255,255,255,0.3);
        animation: anx-dot 1.4s infinite;
      }

      .anx-typing span:nth-child(2) { animation-delay: 0.2s; }
      .anx-typing span:nth-child(3) { animation-delay: 0.4s; }

      @keyframes anx-dot {
        0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
        30% { transform: translateY(-6px); opacity: 1; }
      }

      #anx-input-area {
        padding: 12px 16px;
        border-top: 1px solid rgba(255,255,255,0.06);
        display: flex;
        gap: 8px;
        align-items: center;
        flex-shrink: 0;
        background: #0d0d14;
      }

      #anx-input {
        flex: 1;
        border: 1px solid rgba(255,255,255,0.1);
        background: rgba(255,255,255,0.04);
        border-radius: 10px;
        padding: 10px 14px;
        color: #e0e0e5;
        font-size: 13.5px;
        outline: none;
        transition: border-color 0.2s;
        resize: none;
        max-height: 80px;
        min-height: 40px;
        line-height: 1.4;
        font-family: inherit;
      }

      #anx-input::placeholder {
        color: rgba(255,255,255,0.25);
      }

      #anx-input:focus {
        border-color: ${BRAND_COLOR}44;
      }

      #anx-send {
        width: 38px;
        height: 38px;
        border: none;
        background: ${BRAND_COLOR};
        border-radius: 10px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: opacity 0.2s, transform 0.15s;
        flex-shrink: 0;
      }

      #anx-send:hover { opacity: 0.85; }
      #anx-send:active { transform: scale(0.92); }
      #anx-send:disabled { opacity: 0.4; cursor: default; transform: none; }

      #anx-send svg {
        width: 18px;
        height: 18px;
        fill: #0a0a0f;
      }

      #anx-powered {
        text-align: center;
        padding: 6px;
        font-size: 10px;
        color: rgba(255,255,255,0.2);
        flex-shrink: 0;
      }

      #anx-powered a {
        color: rgba(255,255,255,0.35);
        text-decoration: none;
      }

      /* Mobile responsive */
      @media (max-width: 480px) {
        #anx-window {
          width: 100%;
          height: 100%;
          bottom: 0;
          right: 0;
          border-radius: 0;
        }
        #anx-bubble {
          bottom: 16px;
          right: 16px;
        }
      }

      /* Booking UI */
      #anx-booking {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.1) transparent;
      }

      #anx-booking-btn {
        width: 30px;
        height: 30px;
        border: none;
        background: rgba(255,255,255,0.06);
        border-radius: 8px;
        cursor: pointer;
        color: rgba(255,255,255,0.5);
        font-size: 16px;
        display: none;
        align-items: center;
        justify-content: center;
        transition: background 0.2s, color 0.2s;
      }
      #anx-booking-btn:hover { background: rgba(255,255,255,0.12); color: #fff; }

      .anx-booking-title {
        font-size: 15px;
        font-weight: 600;
        color: #fff;
        text-align: center;
        margin-bottom: 4px;
      }

      .anx-booking-back {
        background: none;
        border: none;
        color: rgba(255,255,255,0.5);
        cursor: pointer;
        font-size: 12px;
        padding: 4px 0;
        text-align: left;
      }
      .anx-booking-back:hover { color: #fff; }

      /* Date picker */
      .anx-cal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      .anx-cal-header span {
        color: #fff;
        font-size: 14px;
        font-weight: 600;
      }
      .anx-cal-nav {
        background: none;
        border: none;
        color: rgba(255,255,255,0.5);
        cursor: pointer;
        font-size: 18px;
        padding: 4px 8px;
      }
      .anx-cal-nav:hover { color: #fff; }
      .anx-cal-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 4px;
        text-align: center;
      }
      .anx-cal-dow {
        font-size: 10px;
        color: rgba(255,255,255,0.35);
        padding: 4px 0;
        text-transform: uppercase;
      }
      .anx-cal-day {
        padding: 8px 4px;
        border-radius: 6px;
        font-size: 13px;
        color: #e0e0e5;
        cursor: pointer;
        border: none;
        background: none;
        transition: background 0.15s;
      }
      .anx-cal-day:hover { background: rgba(255,255,255,0.08); }
      .anx-cal-day.disabled { color: rgba(255,255,255,0.15); pointer-events: none; }
      .anx-cal-day.today { border: 1px solid ${BRAND_COLOR}44; }
      .anx-cal-day.selected { background: ${BRAND_COLOR}; color: #0a0a0f; font-weight: 600; }
      .anx-cal-day.empty { pointer-events: none; }

      /* Time slots */
      .anx-slots-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 6px;
      }
      .anx-slot-btn {
        padding: 10px 4px;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
        background: rgba(255,255,255,0.04);
        color: #e0e0e5;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.15s;
      }
      .anx-slot-btn:hover { border-color: ${BRAND_COLOR}66; background: rgba(255,255,255,0.06); }
      .anx-slot-btn.selected { background: ${BRAND_COLOR}; color: #0a0a0f; border-color: ${BRAND_COLOR}; font-weight: 600; }
      .anx-slots-empty {
        color: rgba(255,255,255,0.4);
        font-size: 13px;
        text-align: center;
        padding: 16px 0;
      }

      /* Contact form */
      .anx-form-group { display: flex; flex-direction: column; gap: 4px; }
      .anx-form-label { font-size: 11px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
      .anx-form-input {
        padding: 10px 12px;
        border: 1px solid rgba(255,255,255,0.1);
        background: rgba(255,255,255,0.04);
        border-radius: 8px;
        color: #e0e0e5;
        font-size: 13px;
        outline: none;
        font-family: inherit;
      }
      .anx-form-input:focus { border-color: ${BRAND_COLOR}44; }
      .anx-form-input::placeholder { color: rgba(255,255,255,0.25); }
      .anx-book-submit {
        padding: 12px;
        background: ${BRAND_COLOR};
        color: #0a0a0f;
        border: none;
        border-radius: 10px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.15s;
      }
      .anx-book-submit:hover { opacity: 0.85; }
      .anx-book-submit:disabled { opacity: 0.5; cursor: default; }

      /* Confirmation */
      .anx-confirm-check {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: ${BRAND_COLOR};
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 8px auto;
        font-size: 24px;
        color: #0a0a0f;
      }
      .anx-confirm-title {
        text-align: center;
        font-size: 16px;
        font-weight: 600;
        color: #fff;
      }
      .anx-confirm-detail {
        text-align: center;
        font-size: 13px;
        color: rgba(255,255,255,0.5);
      }
      .anx-confirm-back {
        padding: 10px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        color: #e0e0e5;
        font-size: 13px;
        cursor: pointer;
        text-align: center;
        margin-top: 8px;
      }
      .anx-confirm-back:hover { background: rgba(255,255,255,0.1); }
    `;
    document.head.appendChild(style);
  }

  // --- Widget DOM ---
  function createWidget() {
    const container = document.createElement("div");
    container.id = "anx-container";

    // Bubble
    container.innerHTML = `
      <div id="anx-bubble">
        <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>
        <div id="anx-badge">1</div>
      </div>
      <div id="anx-window">
        <div id="anx-header">
          <div id="anx-header-info">
            <div id="anx-header-avatar">A</div>
            <div id="anx-header-text">
              <h3 id="anx-title">Aria</h3>
              <p><span class="anx-header-status"></span>Typically replies instantly</p>
            </div>
          </div>
          <div id="anx-header-actions">
            <button id="anx-booking-btn" title="Book Appointment">&#128197;</button>
            <button id="anx-minimize" title="Minimize">&#8722;</button>
            <button id="anx-close" title="Close">&times;</button>
          </div>
        </div>
        <div id="anx-booking"></div>
        <div id="anx-messages"></div>
        <div id="anx-input-area">
          <textarea id="anx-input" placeholder="Type a message..." rows="1"></textarea>
          <button id="anx-send" title="Send">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>
        <div id="anx-powered">Powered by <a href="https://agentnexlify.com" target="_blank" rel="noopener">AgentNexLiFy</a></div>
      </div>
    `;

    document.body.appendChild(container);
    return container;
  }

  // --- State ---
  let isOpen = false;
  let isLoading = false;
  let hasAutoOpened = false;
  let unreadCount = 0;
  let botName = "Aria";
  let agentName = "Agent";

  // Booking state
  let tenantId = "";
  let bookingEnabled = false;
  let bookingStep = null; // null | "date" | "slots" | "form" | "confirmed"
  let selectedDate = null;
  let availableSlots = [];
  let selectedSlot = null;
  let bookingMaxDays = 30;

  // --- API calls ---
  async function fetchConfig() {
    try {
      const resp = await fetch(
        `${API_BASE}/api/v1/widget/config/${encodeURIComponent(API_KEY)}`
      );
      if (!resp.ok) return;
      const data = await resp.json();
      botName = data.bot_name || "Aria";
      agentName = data.agent_name || "Agent";
      tenantId = data.tenant_id || "";
      bookingEnabled = data.booking_enabled || false;
    } catch (e) {
      console.warn("AgentNexLiFy: Failed to fetch config", e);
    }
  }

  async function fetchHistory() {
    // History is loaded from localStorage session; no dedicated history endpoint
    return [];
  }

  async function sendMessage(text) {
    if (!API_KEY || !API_BASE) {
      throw new Error("Widget not configured: missing data-api-key or data-api-base");
    }
    const resp = await fetch(`${API_BASE}/api/v1/widget/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: API_KEY,
        session_id: getSessionId(),
        message: text,
      }),
    });
    if (!resp.ok) {
      const err = await resp.text().catch(() => "");
      throw new Error(`HTTP ${resp.status}: ${err}`);
    }
    return resp.json();
  }

  // --- DOM helpers ---
  function addMessage(role, text) {
    const container = document.getElementById("anx-messages");
    const div = document.createElement("div");
    div.className = `anx-msg ${role}`;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    // Notification when minimized
    if (!isOpen && role === "assistant") {
      unreadCount++;
      const badge = document.getElementById("anx-badge");
      badge.textContent = unreadCount;
      badge.style.display = "flex";
    }
  }

  function disableWidgetInput(reason) {
    const input = document.getElementById("anx-input");
    const sendBtn = document.getElementById("anx-send");
    const inputArea = document.getElementById("anx-input-area");
    if (input) {
      input.disabled = true;
      input.placeholder = reason;
    }
    if (sendBtn) sendBtn.disabled = true;

    if (inputArea && !document.getElementById("anx-upgrade-bar")) {
      const bar = document.createElement("div");
      bar.id = "anx-upgrade-bar";
      bar.style.cssText =
        "padding:10px 16px;text-align:center;background:#1a1a25;border-top:1px solid rgba(255,255,255,0.06);flex-shrink:0;";
      const btn = document.createElement("a");
      btn.href = API_BASE.replace(/\/api.*$/, "").replace(/:\d+$/, "") + "/pricing";
      btn.target = "_blank";
      btn.rel = "noopener";
      btn.textContent = "Upgrade Now";
      btn.style.cssText =
        "display:inline-block;padding:8px 24px;background:" +
        BRAND_COLOR +
        ";color:#0a0a0f;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;";
      bar.appendChild(btn);
      inputArea.parentNode.insertBefore(bar, inputArea.nextSibling);
    }
  }

  function showTyping() {
    const container = document.getElementById("anx-messages");
    const div = document.createElement("div");
    div.className = "anx-typing";
    div.id = "anx-typing-indicator";
    div.innerHTML = "<span></span><span></span><span></span>";
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById("anx-typing-indicator");
    if (el) el.remove();
  }

  function updateHeader() {
    const title = document.getElementById("anx-title");
    const avatar = document.getElementById("anx-header-avatar");
    if (title) title.textContent = `${botName} \u2022 ${agentName}'s AI Assistant`;
    if (avatar) avatar.textContent = botName.charAt(0).toUpperCase();
  }

  // --- Event handlers ---
  function toggleWindow(open) {
    const win = document.getElementById("anx-window");
    const bubble = document.getElementById("anx-bubble");
    isOpen = open;

    if (open) {
      win.classList.add("open");
      bubble.classList.add("hidden");
      unreadCount = 0;
      document.getElementById("anx-badge").style.display = "none";
      document.getElementById("anx-input").focus();
      localStorage.setItem(STATE_KEY, "open");
    } else {
      win.classList.remove("open");
      bubble.classList.remove("hidden");
      localStorage.setItem(STATE_KEY, "closed");
    }
  }

  async function handleSend() {
    const input = document.getElementById("anx-input");
    const text = input.value.trim();
    if (!text || isLoading) return;

    // Booking intent detection
    if (bookingEnabled && tenantId && /\b(book|appointment|schedule|available|booking)\b/i.test(text)) {
      input.value = "";
      input.style.height = "auto";
      addMessage("user", text);
      addMessage("assistant", "I can help you book an appointment! Let me show you our available times.");
      setTimeout(() => showBooking("date"), 500);
      return;
    }

    input.value = "";
    input.style.height = "auto";
    addMessage("user", text);

    isLoading = true;
    document.getElementById("anx-send").disabled = true;
    showTyping();

    try {
      const data = await sendMessage(text);
      hideTyping();
      addMessage("assistant", data.response);

      // Handle trial expiry
      if (data.trial_expired) {
        disableWidgetInput("Your free trial has expired.");
      }
    } catch (e) {
      hideTyping();
      addMessage(
        "assistant",
        "Sorry, I'm having trouble connecting. Please try again in a moment!"
      );
      console.error("AgentNexLiFy: Send failed", e);
    } finally {
      isLoading = false;
      document.getElementById("anx-send").disabled = false;
    }
  }

  // --- Auto-resize textarea ---
  function autoResize(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 80) + "px";
  }

  // --- Booking UI ---

  function showBooking(step) {
    bookingStep = step;
    const booking = document.getElementById("anx-booking");
    const messages = document.getElementById("anx-messages");
    const inputArea = document.getElementById("anx-input-area");

    if (!step) {
      booking.style.display = "none";
      booking.innerHTML = "";
      messages.style.display = "flex";
      inputArea.style.display = "flex";
      return;
    }

    messages.style.display = "none";
    inputArea.style.display = "none";
    booking.style.display = "flex";

    if (step === "date") renderDatePicker();
    else if (step === "slots") renderSlots();
    else if (step === "form") renderContactForm();
    else if (step === "confirmed") renderConfirmation();
  }

  function renderDatePicker() {
    const booking = document.getElementById("anx-booking");
    const now = new Date();
    const viewMonth = selectedDate ? new Date(selectedDate) : new Date(now);
    viewMonth.setDate(1);

    const year = viewMonth.getFullYear();
    const month = viewMonth.getMonth();
    const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDow = new Date(year, month, 1).getDay();
    const today = new Date(); today.setHours(0,0,0,0);
    const maxDate = new Date(today); maxDate.setDate(maxDate.getDate() + bookingMaxDays);

    let html = `<button class="anx-booking-back" onclick="document.getElementById('anx-booking').__anxBack()">&#8592; Back to chat</button>`;
    html += `<div class="anx-booking-title">Select a Date</div>`;
    html += `<div class="anx-cal-header">`;
    html += `<button class="anx-cal-nav" data-dir="-1">&#8249;</button>`;
    html += `<span>${monthNames[month]} ${year}</span>`;
    html += `<button class="anx-cal-nav" data-dir="1">&#8250;</button>`;
    html += `</div>`;
    html += `<div class="anx-cal-grid">`;
    ["Su","Mo","Tu","We","Th","Fr","Sa"].forEach(d => { html += `<div class="anx-cal-dow">${d}</div>`; });
    for (let i = 0; i < firstDow; i++) html += `<button class="anx-cal-day empty"></button>`;
    for (let d = 1; d <= daysInMonth; d++) {
      const dt = new Date(year, month, d);
      const isPast = dt < today;
      const isBeyond = dt > maxDate;
      const isToday = dt.getTime() === today.getTime();
      const isSel = selectedDate && dt.toDateString() === new Date(selectedDate).toDateString();
      let cls = "anx-cal-day";
      if (isPast || isBeyond) cls += " disabled";
      if (isToday) cls += " today";
      if (isSel) cls += " selected";
      html += `<button class="${cls}" data-date="${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}">${d}</button>`;
    }
    html += `</div>`;

    booking.innerHTML = html;

    // Back to chat
    booking.__anxBack = () => showBooking(null);

    // Month nav
    booking.querySelectorAll(".anx-cal-nav").forEach(btn => {
      btn.addEventListener("click", () => {
        const dir = parseInt(btn.dataset.dir);
        const nv = new Date(year, month + dir, 1);
        selectedDate = nv.toISOString().split("T")[0];
        renderDatePicker();
      });
    });

    // Day selection
    booking.querySelectorAll(".anx-cal-day:not(.disabled):not(.empty)").forEach(btn => {
      btn.addEventListener("click", () => {
        selectedDate = btn.dataset.date;
        showBooking("slots");
      });
    });
  }

  async function renderSlots() {
    const booking = document.getElementById("anx-booking");
    booking.innerHTML = `<button class="anx-booking-back" onclick="document.getElementById('anx-booking').__anxBack()">&#8592; Back</button><div class="anx-booking-title">Available Times</div><div class="anx-slots-empty">Loading...</div>`;
    booking.__anxBack = () => { showBooking("date"); };

    try {
      const resp = await fetch(
        `${API_BASE}/api/v1/appointments/slots/${tenantId}?date=${selectedDate}&api_key=${encodeURIComponent(API_KEY)}`
      );
      if (!resp.ok) throw new Error("Failed to fetch slots");
      const data = await resp.json();
      availableSlots = data.slots || [];
    } catch (e) {
      console.error("AgentNexLiFy: Slots fetch failed", e);
      availableSlots = [];
    }

    let html = `<button class="anx-booking-back" onclick="document.getElementById('anx-booking').__anxBack()">&#8592; Back</button>`;
    html += `<div class="anx-booking-title">${formatBookingDate(selectedDate)}</div>`;

    if (availableSlots.length === 0) {
      html += `<div class="anx-slots-empty">No available slots for this date. Please try another day.</div>`;
    } else {
      html += `<div class="anx-slots-grid">`;
      availableSlots.forEach((slot, i) => {
        html += `<button class="anx-slot-btn" data-idx="${i}">${slot.start}</button>`;
      });
      html += `</div>`;
    }

    booking.innerHTML = html;
    booking.__anxBack = () => { showBooking("date"); };

    booking.querySelectorAll(".anx-slot-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        selectedSlot = availableSlots[parseInt(btn.dataset.idx)];
        booking.querySelectorAll(".anx-slot-btn").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        setTimeout(() => showBooking("form"), 300);
      });
    });
  }

  function renderContactForm() {
    const booking = document.getElementById("anx-booking");
    let html = `<button class="anx-booking-back" onclick="document.getElementById('anx-booking').__anxBack()">&#8592; Back</button>`;
    html += `<div class="anx-booking-title">Your Details</div>`;
    html += `<div style="text-align:center;font-size:12px;color:rgba(255,255,255,0.4);margin-bottom:4px;">${formatBookingDate(selectedDate)} at ${selectedSlot.start}</div>`;
    html += `<div class="anx-form-group"><label class="anx-form-label">Name *</label><input class="anx-form-input" id="anx-book-name" placeholder="Your name" required></div>`;
    html += `<div class="anx-form-group"><label class="anx-form-label">Email *</label><input class="anx-form-input" id="anx-book-email" type="email" placeholder="your@email.com" required></div>`;
    html += `<div class="anx-form-group"><label class="anx-form-label">Phone</label><input class="anx-form-input" id="anx-book-phone" type="tel" placeholder="(optional)"></div>`;
    html += `<div class="anx-form-group"><label class="anx-form-label">Notes</label><input class="anx-form-input" id="anx-book-notes" placeholder="(optional)"></div>`;
    html += `<button class="anx-book-submit" id="anx-book-confirm">Confirm Appointment</button>`;
    html += `<div id="anx-book-error" style="color:#ff4444;font-size:12px;text-align:center;display:none;"></div>`;

    booking.innerHTML = html;
    booking.__anxBack = () => { showBooking("slots"); };

    document.getElementById("anx-book-confirm").addEventListener("click", submitBooking);
  }

  async function submitBooking() {
    const name = document.getElementById("anx-book-name").value.trim();
    const email = document.getElementById("anx-book-email").value.trim();
    const phone = document.getElementById("anx-book-phone").value.trim();
    const notes = document.getElementById("anx-book-notes").value.trim();
    const errEl = document.getElementById("anx-book-error");
    const btn = document.getElementById("anx-book-confirm");

    if (!name || !email) {
      errEl.textContent = "Name and email are required.";
      errEl.style.display = "block";
      return;
    }

    btn.disabled = true;
    btn.textContent = "Booking...";
    errEl.style.display = "none";

    try {
      const resp = await fetch(`${API_BASE}/api/v1/appointments/${tenantId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: API_KEY,
          customer_name: name,
          customer_email: email,
          customer_phone: phone || null,
          start_utc: selectedSlot.start_utc,
          end_utc: selectedSlot.end_utc,
          notes: notes || null,
        }),
      });

      if (resp.status === 409) {
        errEl.textContent = "This slot was just taken. Please select another time.";
        errEl.style.display = "block";
        btn.disabled = false;
        btn.textContent = "Confirm Appointment";
        setTimeout(() => showBooking("slots"), 1500);
        return;
      }

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      showBooking("confirmed");
    } catch (e) {
      console.error("AgentNexLiFy: Booking failed", e);
      errEl.textContent = "Something went wrong. Please try again.";
      errEl.style.display = "block";
      btn.disabled = false;
      btn.textContent = "Confirm Appointment";
    }
  }

  function renderConfirmation() {
    const booking = document.getElementById("anx-booking");
    let html = `<div class="anx-confirm-check">&#10003;</div>`;
    html += `<div class="anx-confirm-title">Appointment Confirmed!</div>`;
    html += `<div class="anx-confirm-detail">${formatBookingDate(selectedDate)} at ${selectedSlot.start}</div>`;
    html += `<button class="anx-confirm-back" id="anx-book-done">Back to Chat</button>`;
    booking.innerHTML = html;

    document.getElementById("anx-book-done").addEventListener("click", () => {
      bookingStep = null;
      selectedDate = null;
      selectedSlot = null;
      availableSlots = [];
      showBooking(null);
    });
  }

  function formatBookingDate(dateStr) {
    const d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  }

  // --- Initialization ---
  async function init() {
    if (!API_KEY) {
      console.error("AgentNexLiFy: Missing data-api-key attribute");
      return;
    }

    injectStyles();
    createWidget();

    await fetchConfig();
    updateHeader();

    // Show booking button if enabled
    if (bookingEnabled && tenantId) {
      const bookBtn = document.getElementById("anx-booking-btn");
      if (bookBtn) {
        bookBtn.style.display = "flex";
        bookBtn.addEventListener("click", () => showBooking("date"));
      }
    }

    // Load existing history
    const history = await fetchHistory();
    for (const msg of history) {
      if (msg.role === "user" || msg.role === "assistant") {
        addMessage(msg.role, msg.content);
      }
    }

    // Event listeners
    document
      .getElementById("anx-bubble")
      .addEventListener("click", () => toggleWindow(true));
    document
      .getElementById("anx-minimize")
      .addEventListener("click", () => toggleWindow(false));
    document
      .getElementById("anx-close")
      .addEventListener("click", () => toggleWindow(false));
    document
      .getElementById("anx-send")
      .addEventListener("click", handleSend);

    const input = document.getElementById("anx-input");
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
    input.addEventListener("input", () => autoResize(input));

    // Auto-open after 5 seconds if no history and not manually closed
    const savedState = localStorage.getItem(STATE_KEY);
    if (savedState === "open") {
      toggleWindow(true);
    } else if (history.length === 0 && savedState !== "closed") {
      setTimeout(() => {
        if (!isOpen && !hasAutoOpened) {
          hasAutoOpened = true;
          toggleWindow(true);
          // Send initial greeting
          if (
            document.getElementById("anx-messages").children.length === 0
          ) {
            triggerGreeting();
          }
        }
      }, 5000);
    }
  }

  async function triggerGreeting() {
    showTyping();
    try {
      const data = await sendMessage("hi");
      hideTyping();
      addMessage("assistant", data.response);
    } catch (e) {
      hideTyping();
      addMessage(
        "assistant",
        `Hey there! How can I help you today?`
      );
    }
  }

  // --- Run ---
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
