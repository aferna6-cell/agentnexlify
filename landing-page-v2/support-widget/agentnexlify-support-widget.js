/*
 * AgentNexLiFy support widget - for the marketing site (agentnexlify.com).
 *
 * A self-contained support chatbot: visitors ask product questions and report
 * issues. Conversations are emailed to the platform owner (new-chat heads-up,
 * explicit issue reports, and a full transcript when the chat closes).
 *
 * Distinct from the tenant lead-capture widget (widget/agentnexlify-widget.js),
 * which is byte-identical-locked and embedded on customers' own sites.
 *
 * Embed:
 *   <script async src="support-widget/agentnexlify-support-widget.js"
 *           data-api-base="https://app.agentnexlify.com"></script>
 */
(function () {
  "use strict";

  var script =
    document.currentScript ||
    (function () {
      var s = document.getElementsByTagName("script");
      return s[s.length - 1];
    })();
  var API_BASE = (
    (script && script.getAttribute("data-api-base")) ||
    "https://app.agentnexlify.com"
  ).replace(/\/+$/, "");
  var ENDPOINT = API_BASE + "/api/v1/platform-support";

  // Stable per-tab session id.
  var SESSION_KEY = "anlf_support_session";
  var sessionId;
  try {
    sessionId = sessionStorage.getItem(SESSION_KEY);
    if (!sessionId) {
      sessionId = uuid();
      sessionStorage.setItem(SESSION_KEY, sessionId);
    }
  } catch (e) {
    sessionId = uuid();
  }

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  var GREETING =
    "Hi! I'm the AgentNexLiFy support assistant. Ask me anything about the " +
    "product, or report an issue and we'll follow up by email.";

  var started = false; // any message sent yet?
  var endSent = false;
  var open = false;

  // --- styles ---------------------------------------------------------------
  var css =
    ".anlf-sw *{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}" +
    ".anlf-sw-btn{position:fixed;right:20px;bottom:20px;width:60px;height:60px;border-radius:50%;background:#1f6feb;color:#fff;border:none;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);font-size:26px;line-height:1;z-index:2147483000}" +
    ".anlf-sw-btn:hover{background:#1a5fd0}" +
    ".anlf-sw-panel{position:fixed;right:20px;bottom:92px;width:360px;max-width:calc(100vw - 40px);height:520px;max-height:calc(100vh - 120px);background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.4);display:none;flex-direction:column;overflow:hidden;z-index:2147483000}" +
    ".anlf-sw-panel.open{display:flex}" +
    ".anlf-sw-head{background:#161b22;padding:14px 16px;border-bottom:1px solid #30363d;font-weight:600;display:flex;justify-content:space-between;align-items:center}" +
    ".anlf-sw-close{background:none;border:none;color:#8b949e;font-size:20px;cursor:pointer;line-height:1}" +
    ".anlf-sw-msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}" +
    ".anlf-sw-msg{padding:9px 12px;border-radius:10px;max-width:85%;font-size:14px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word}" +
    ".anlf-sw-msg.bot{background:#21262d;align-self:flex-start;border-bottom-left-radius:3px}" +
    ".anlf-sw-msg.user{background:#1f6feb;color:#fff;align-self:flex-end;border-bottom-right-radius:3px}" +
    ".anlf-sw-foot{border-top:1px solid #30363d;padding:10px}" +
    ".anlf-sw-row{display:flex;gap:8px}" +
    ".anlf-sw-input,.anlf-sw-area{flex:1;background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:8px;padding:9px 10px;font-size:14px;resize:none}" +
    ".anlf-sw-send{background:#1f6feb;color:#fff;border:none;border-radius:8px;padding:0 14px;cursor:pointer;font-size:14px}" +
    ".anlf-sw-send:disabled{opacity:.5;cursor:default}" +
    ".anlf-sw-link{display:inline-block;margin-top:8px;color:#58a6ff;font-size:12px;cursor:pointer;background:none;border:none;padding:0}" +
    ".anlf-sw-report{display:none;flex-direction:column;gap:8px;margin-top:8px}" +
    ".anlf-sw-report.open{display:flex}" +
    ".anlf-sw-note{font-size:12px;color:#8b949e;text-align:center;margin-top:6px}";

  var styleEl = document.createElement("style");
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // --- DOM ------------------------------------------------------------------
  var root = document.createElement("div");
  root.className = "anlf-sw";
  root.innerHTML =
    '<button class="anlf-sw-btn" aria-label="Open support chat">&#128172;</button>' +
    '<div class="anlf-sw-panel" role="dialog" aria-label="Support chat">' +
    '  <div class="anlf-sw-head"><span>AgentNexLiFy Support</span>' +
    '    <button class="anlf-sw-close" aria-label="Close">&times;</button></div>' +
    '  <div class="anlf-sw-msgs"></div>' +
    '  <div class="anlf-sw-foot">' +
    '    <div class="anlf-sw-row">' +
    '      <input class="anlf-sw-input" type="text" placeholder="Type your question..." />' +
    '      <button class="anlf-sw-send">Send</button>' +
    "    </div>" +
    '    <button class="anlf-sw-link" data-act="toggle-report">Report an issue</button>' +
    '    <div class="anlf-sw-report">' +
    '      <input class="anlf-sw-input anlf-sw-remail" type="email" placeholder="Your email" />' +
    '      <textarea class="anlf-sw-area anlf-sw-rmsg" rows="3" placeholder="Describe the issue..."></textarea>' +
    '      <button class="anlf-sw-send anlf-sw-rsend">Send report</button>' +
    "    </div>" +
    '    <div class="anlf-sw-note">We typically respond within 24 hours.</div>' +
    "  </div>" +
    "</div>";
  document.body.appendChild(root);

  var btn = root.querySelector(".anlf-sw-btn");
  var panel = root.querySelector(".anlf-sw-panel");
  var closeBtn = root.querySelector(".anlf-sw-close");
  var msgs = root.querySelector(".anlf-sw-msgs");
  var input = root.querySelector(".anlf-sw-input");
  var sendBtn = root.querySelector(".anlf-sw-send");
  var reportLink = root.querySelector('[data-act="toggle-report"]');
  var reportBox = root.querySelector(".anlf-sw-report");
  var reportEmail = root.querySelector(".anlf-sw-remail");
  var reportMsg = root.querySelector(".anlf-sw-rmsg");
  var reportSend = root.querySelector(".anlf-sw-rsend");

  function addMsg(text, who) {
    var el = document.createElement("div");
    el.className = "anlf-sw-msg " + (who === "user" ? "user" : "bot");
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
  }

  function pageUrl() {
    try {
      return location.href.slice(0, 500);
    } catch (e) {
      return null;
    }
  }

  function openPanel() {
    if (open) return;
    open = true;
    panel.classList.add("open");
    if (!msgs.childNodes.length) addMsg(GREETING, "bot");
    input.focus();
  }

  function closePanel() {
    open = false;
    panel.classList.remove("open");
  }

  btn.addEventListener("click", function () {
    open ? closePanel() : openPanel();
  });
  closeBtn.addEventListener("click", closePanel);

  reportLink.addEventListener("click", function () {
    reportBox.classList.toggle("open");
  });

  function sendChat() {
    var text = (input.value || "").trim();
    if (!text) return;
    input.value = "";
    addMsg(text, "user");
    started = true;
    sendBtn.disabled = true;
    var thinking = addMsg("…", "bot");
    fetch(ENDPOINT + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: text,
        page_url: pageUrl(),
      }),
    })
      .then(function (r) {
        return r.ok ? r.json() : Promise.reject(r);
      })
      .then(function (data) {
        thinking.textContent =
          (data && data.reply) ||
          "Sorry, something went wrong. Try again or report an issue.";
      })
      .catch(function () {
        thinking.textContent =
          "Sorry, I couldn't reach support right now. Please try again.";
      })
      .finally(function () {
        sendBtn.disabled = false;
        msgs.scrollTop = msgs.scrollHeight;
      });
  }

  sendBtn.addEventListener("click", sendChat);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendChat();
  });

  reportSend.addEventListener("click", function () {
    var email = (reportEmail.value || "").trim();
    var text = (reportMsg.value || "").trim();
    if (!email || !text) {
      addMsg("Please add your email and a short description.", "bot");
      return;
    }
    started = true;
    reportSend.disabled = true;
    fetch(ENDPOINT + "/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        email: email,
        message: text,
        page_url: pageUrl(),
      }),
    })
      .then(function (r) {
        return r.ok ? r.json() : Promise.reject(r);
      })
      .then(function (data) {
        reportBox.classList.remove("open");
        reportMsg.value = "";
        addMsg(
          (data && data.message) ||
            "Thanks - your report is on its way. We'll email you back.",
          "bot"
        );
      })
      .catch(function () {
        addMsg("Couldn't send the report. Email help@agentnexlify.com instead.", "bot");
      })
      .finally(function () {
        reportSend.disabled = false;
      });
  });

  // Email the owner a full transcript when the visitor leaves. sendBeacon
  // survives unload; idempotent server-side so duplicate fires are harmless.
  function endSession() {
    if (endSent || !started) return;
    endSent = true;
    var payload = JSON.stringify({ session_id: sessionId });
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(
          ENDPOINT + "/end",
          new Blob([payload], { type: "application/json" })
        );
        return;
      }
    } catch (e) {
      /* fall through to fetch */
    }
    try {
      fetch(ENDPOINT + "/end", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
        keepalive: true,
      });
    } catch (e) {
      /* best-effort */
    }
  }

  window.addEventListener("pagehide", endSession);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") endSession();
  });
})();
