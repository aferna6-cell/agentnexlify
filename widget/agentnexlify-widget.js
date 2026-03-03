(function () {
  "use strict";

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
  const STATE_KEY = "anx_widget_state";

  // --- Session Management ---
  function getSessionId() {
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid =
        "web_" +
        Date.now().toString(36) +
        "_" +
        Math.random().toString(36).slice(2, 10);
      localStorage.setItem(SESSION_KEY, sid);
    }
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
        fill: #0a0a0f;
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
            <button id="anx-minimize" title="Minimize">&#8722;</button>
            <button id="anx-close" title="Close">&times;</button>
          </div>
        </div>
        <div id="anx-messages"></div>
        <div id="anx-input-area">
          <textarea id="anx-input" placeholder="Type a message..." rows="1"></textarea>
          <button id="anx-send" title="Send">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>
        <div id="anx-powered">Powered by <a href="#">AgentNexLiFy</a></div>
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
    } catch (e) {
      console.warn("AgentNexLiFy: Failed to fetch config", e);
    }
  }

  async function fetchHistory() {
    // History is loaded from localStorage session; no dedicated history endpoint
    return [];
  }

  async function sendMessage(text) {
    const resp = await fetch(`${API_BASE}/api/v1/widget/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: API_KEY,
        session_id: getSessionId(),
        message: text,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
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
