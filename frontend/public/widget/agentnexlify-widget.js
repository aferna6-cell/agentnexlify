(function () {
  "use strict";

  // --- Double-init guard ---
  if (window.__agentNexlifyWidget) return;
  window.__agentNexlifyWidget = true;

  // --- Configuration ---
  const scriptTag = document.currentScript;
  const API_KEY = scriptTag?.getAttribute("data-api-key") || "";
  const BRAND_COLOR = scriptTag?.getAttribute("data-brand-color") || "#6cff5c";
  const API_BASE =
    scriptTag?.getAttribute("data-api-base") ||
    scriptTag?.src?.replace(/\/widget\/agentnexlify-widget\.js.*$/, "") ||
    "";

  // --- i18n: Language resolution ---
  // Order: (1) data-language attribute, (2) navigator.language startsWith "es", (3) "en"
  (function () {
    const attr = (scriptTag?.getAttribute("data-language") || "").toLowerCase().trim();
    if (attr === "es" || attr === "en") { window.__anxLang = attr; return; }
    if (typeof navigator !== "undefined" && navigator.language &&
        navigator.language.toLowerCase().startsWith("es")) { window.__anxLang = "es"; return; }
    window.__anxLang = "en";
  })();
  const lang = window.__anxLang;

  // --- i18n: UI Strings ---
  const STRINGS = {
    en: {
      // Input area
      inputPlaceholder: "Type a message...",
      sendTitle: "Send",
      attachTitle: "Attach file",
      contentModePlaceholder: "Paste content, URL, or YouTube link to repurpose...",
      fillFormFirst: "Fill out the form above to start chatting...",
      teamMemberWillRespond: "A team member will respond...",
      trialExpired: "Your free trial has expired.",
      // Header
      typicallyReplies: "Typically replies instantly",
      minimizeTitle: "Minimize",
      closeTitle: "Close",
      viewMenuTitle: "View Menu",
      bookTitle: "Book Appointment",
      contentModeTitle: "Content Mode",
      currentlyOffline: "Currently offline",
      // Errors / notices
      connectError: "Sorry, I'm having trouble connecting. Please try again in a moment!",
      fileTooLarge: "File is too large. Please send files under 5 MB.",
      uploadError: "Sorry, I couldn't upload that file. Please try again.",
      // Booking
      backToChat: "Back to chat",
      selectDate: "Select a Date",
      back: "Back",
      availableTimes: "Available Times",
      loading: "Loading...",
      noSlots: "No available slots for this date. Please try another day.",
      yourDetails: "Your Details",
      labelName: "Name *",
      labelEmail: "Email *",
      labelPhone: "Phone",
      labelReason: "Reason for Visit",
      labelNotes: "Notes",
      confirmAppointment: "Confirm Appointment",
      booking: "Booking...",
      nameEmailRequired: "Name and email are required.",
      slotTaken: "This slot was just taken. Please select another time.",
      bookingError: "Something went wrong. Please try again.",
      appointmentConfirmed: "Appointment Confirmed!",
      backToChat2: "Back to Chat",
      bookingIntentResponse: "I can help you book an appointment! Let me show you our available times.",
      // Contact form labels/placeholders
      yourNamePlaceholder: "Your name",
      yourEmailPlaceholder: "your@email.com",
      optionalPlaceholder: "(optional)",
      // Offline form
      offlineLabelMessage: "Message *",
      offlineMessagePlaceholder: "How can we help you?",
      sendMessage: "Send Message",
      nameEmailMessageRequired: "Name, email, and message are required.",
      sending: "Sending...",
      messageSent: "Message Sent!",
      offlineThankYou: "We'll get back to you soon.",
      sendAnother: "Send Another Message",
      genericError: "Something went wrong. Please try again.",
      // Pre-chat form
      preChatTitle: "Before we start, tell us a bit about yourself:",
      startChat: "Start Chat",
      // Greeting
      greetingFallback: "How can I help you today?",
      greetingPrefix: "Hi! I'm the AI assistant for this business. ",
      // Menu
      menuOrderHint: "Just tell me what you'd like to order!",
      // Upgrade
      upgradeNow: "Upgrade Now",
      // Powered by
      poweredBy: "Powered by",
      // Calendar
      monthNames: ["January","February","March","April","May","June","July","August","September","October","November","December"],
      dayNames: ["Su","Mo","Tu","We","Th","Fr","Sa"],
    },
    es: {
      // Input area
      inputPlaceholder: "Escribe tu mensaje…",
      sendTitle: "Enviar",
      attachTitle: "Adjuntar archivo",
      contentModePlaceholder: "Pega contenido, URL o enlace de YouTube para reutilizar…",
      fillFormFirst: "Completa el formulario de arriba para comenzar a chatear…",
      teamMemberWillRespond: "Un miembro del equipo te responderá…",
      trialExpired: "Tu prueba gratuita ha vencido.",
      // Header
      typicallyReplies: "Normalmente responde al instante",
      minimizeTitle: "Minimizar",
      closeTitle: "Cerrar",
      viewMenuTitle: "Ver menú",
      bookTitle: "Agendar una cita",
      contentModeTitle: "Modo contenido",
      currentlyOffline: "Actualmente sin conexión",
      // Errors / notices
      connectError: "Lo siento, tengo problemas para conectarme. ¡Por favor intenta de nuevo en un momento!",
      fileTooLarge: "El archivo es demasiado grande. Por favor envía archivos de menos de 5 MB.",
      uploadError: "Lo siento, no pude subir ese archivo. Por favor intenta de nuevo.",
      // Booking
      backToChat: "← Volver al chat",
      selectDate: "Selecciona una fecha",
      back: "← Atrás",
      availableTimes: "Horarios disponibles",
      loading: "Cargando…",
      noSlots: "No hay horarios disponibles para este día. Por favor elige otro día.",
      yourDetails: "Tus datos",
      labelName: "Nombre *",
      labelEmail: "Correo electrónico *",
      labelPhone: "Teléfono",
      labelReason: "Motivo de la visita",
      labelNotes: "Notas",
      confirmAppointment: "Confirmar cita",
      booking: "Reservando…",
      nameEmailRequired: "El nombre y el correo electrónico son obligatorios.",
      slotTaken: "Este horario acaba de ser tomado. Por favor elige otro.",
      bookingError: "Algo salió mal. Por favor intenta de nuevo.",
      appointmentConfirmed: "¡Cita confirmada!",
      backToChat2: "Volver al chat",
      bookingIntentResponse: "¡Puedo ayudarte a agendar una cita! Permíteme mostrarte los horarios disponibles.",
      // Contact form labels/placeholders
      yourNamePlaceholder: "Tu nombre",
      yourEmailPlaceholder: "tu@correo.com",
      optionalPlaceholder: "(opcional)",
      // Offline form
      offlineLabelMessage: "Mensaje *",
      offlineMessagePlaceholder: "¿En qué podemos ayudarte?",
      sendMessage: "Enviar mensaje",
      nameEmailMessageRequired: "El nombre, el correo electrónico y el mensaje son obligatorios.",
      sending: "Enviando…",
      messageSent: "¡Mensaje enviado!",
      offlineThankYou: "Te responderemos pronto.",
      sendAnother: "Enviar otro mensaje",
      genericError: "Algo salió mal. Por favor intenta de nuevo.",
      // Pre-chat form
      preChatTitle: "Antes de comenzar, cuéntanos un poco sobre ti:",
      startChat: "Iniciar chat",
      // Greeting
      greetingFallback: "¿En qué puedo ayudarte hoy?",
      greetingPrefix: "¡Hola! Soy el asistente de IA de este negocio. ",
      // Menu
      menuOrderHint: "¡Solo díme qué deseas ordenar!",
      // Upgrade
      upgradeNow: "Mejorar plan",
      // Powered by
      poweredBy: "Desarrollado por",
      // Calendar
      monthNames: ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"],
      dayNames: ["Do","Lu","Ma","Mi","Ju","Vi","Sá"],
    },
  };

  // Shorthand: t(key) returns the string for current language
  function t(key) {
    return (STRINGS[lang] && STRINGS[lang][key] !== undefined)
      ? STRINGS[lang][key]
      : (STRINGS.en[key] !== undefined ? STRINGS.en[key] : key);
  }

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
    // Reset message counter
    msgCounter = 0;
    return sid;
  }

  // --- Styles ---
  function injectStyles() {
    if (document.getElementById("anx-styles")) return;
    const style = document.createElement("style");
    style.id = "anx-styles";
    style.textContent = `
      #anx-container {
        position: fixed !important;
        bottom: 0 !important;
        right: 0 !important;
        z-index: 99997 !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        overflow: visible !important;
        transform: none !important;
        pointer-events: none;
        width: 0;
        height: 0;
      }
      #anx-container * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        visibility: visible !important;
      }

      #anx-bubble {
        position: fixed !important;
        bottom: 24px !important;
        right: 24px !important;
        width: 60px !important;
        height: 60px !important;
        border-radius: 50% !important;
        background: ${BRAND_COLOR} !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3) !important;
        z-index: 99998 !important;
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s;
        animation: anx-pulse 2s infinite;
        pointer-events: auto !important;
        opacity: 1 !important;
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

      #anx-content-mode-btn.active {
        background: rgba(255,255,255,0.2);
        color: #fff;
      }

      #anx-content-mode-badge {
        display: none;
        position: absolute;
        top: -2px;
        right: -2px;
        font-size: 7px;
        background: #22c55e;
        color: #fff;
        border-radius: 50%;
        width: 10px;
        height: 10px;
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

      #anx-attach {
        width: 32px;
        height: 32px;
        border: none;
        background: transparent;
        border-radius: 8px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        opacity: 0.5;
        transition: opacity 0.2s;
      }
      #anx-attach:hover { opacity: 0.8; }
      #anx-attach svg { width: 18px; height: 18px; fill: #e0e0e5; }
      #anx-file-input { display: none; }

      .anx-msg img.anx-attachment {
        max-width: 200px;
        max-height: 160px;
        border-radius: 8px;
        margin-top: 4px;
        cursor: pointer;
      }
      .anx-msg .anx-file-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        background: rgba(255,255,255,0.08);
        border-radius: 6px;
        color: ${BRAND_COLOR};
        text-decoration: none;
        font-size: 12px;
        margin-top: 4px;
      }

      #anx-menu-panel {
        max-height: 320px;
        overflow-y: auto;
        background: rgba(0,0,0,0.15);
        border-bottom: 1px solid rgba(255,255,255,0.06);
        padding: 12px;
      }
      .anx-menu-cat {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: ${BRAND_COLOR};
        margin: 10px 0 6px;
        padding-bottom: 4px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
      }
      .anx-menu-cat:first-child { margin-top: 0; }
      .anx-menu-item {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 6px 0;
        gap: 8px;
      }
      .anx-menu-item-name {
        font-size: 13px;
        font-weight: 500;
        color: #e0e0e5;
      }
      .anx-menu-item-desc {
        font-size: 11px;
        color: rgba(255,255,255,0.4);
        margin-top: 2px;
      }
      .anx-menu-item-price {
        font-size: 13px;
        font-weight: 600;
        color: ${BRAND_COLOR};
        white-space: nowrap;
        flex-shrink: 0;
      }
      .anx-menu-order-hint {
        text-align: center;
        font-size: 11px;
        color: rgba(255,255,255,0.35);
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid rgba(255,255,255,0.06);
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

      @keyframes anxFadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
      #anx-teaser { box-sizing: border-box; }

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

      /* Offline contact form */
      #anx-offline-form {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .anx-offline-msg {
        text-align: center;
        font-size: 13px;
        color: rgba(255,255,255,0.5);
        padding: 4px 0;
        line-height: 1.5;
      }
      .anx-offline-success {
        text-align: center;
        padding: 24px 16px;
      }
      .anx-offline-success-icon {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: ${BRAND_COLOR};
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 12px;
        font-size: 24px;
        color: #0a0a0f;
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
      <div id="anx-teaser" style="display:none;position:fixed;bottom:96px;right:24px;background:#fff;border-radius:12px 12px 4px 12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);padding:10px 14px;max-width:240px;font-size:13px;line-height:1.4;cursor:pointer;animation:anxFadeIn 0.3s ease;z-index:99997;">
        <button id="anx-teaser-close" style="position:absolute;top:4px;right:6px;background:none;border:none;cursor:pointer;font-size:16px;color:#999;line-height:1;" title="Dismiss">&times;</button>
        <p id="anx-teaser-text" style="margin:0;padding-right:12px;color:#333;"></p>
      </div>
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
              <p><span class="anx-header-status"></span>${t('typicallyReplies')}</p>
            </div>
          </div>
          <div id="anx-header-actions">
            <button id="anx-content-mode-btn" title="${t('contentModeTitle')}" style="display:none;position:relative;">&#9998;<span id="anx-content-mode-badge"></span></button>
            <button id="anx-menu-btn" title="${t('viewMenuTitle')}" style="display:none;">&#127860;</button>
            <button id="anx-booking-btn" title="${t('bookTitle')}">&#128197;</button>
            <button id="anx-minimize" title="${t('minimizeTitle')}">&#8722;</button>
            <button id="anx-close" title="${t('closeTitle')}">&times;</button>
          </div>
        </div>
        <div id="anx-menu-panel" style="display:none;"></div>
        <div id="anx-booking"></div>
        <div id="anx-messages"></div>
        <div id="anx-input-area">
          <button id="anx-attach" title="${t('attachTitle')}">
            <svg viewBox="0 0 24 24"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
          <input type="file" id="anx-file-input" accept="image/*,.pdf,.doc,.docx" />
          <textarea id="anx-input" placeholder="${t('inputPlaceholder')}" rows="1"></textarea>
          <button id="anx-send" title="${t('sendTitle')}">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>
        <div id="anx-powered">${t('poweredBy')} <a href="https://agentnexlify.com" target="_blank" rel="noopener">AgentNexLiFy</a></div>
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
  let contentMode = false;
  let msgCounter = 0;
  let botName = "Aria";
  let agentName = "Agent";
  let greetingMessage = "";
  let widgetIsOnline = true;
  let offlineMessage =
    "We are currently offline. Leave your details and we\u2019ll get back to you soon!";

  // Teaser state
  let teaserMessage = "";
  let teaserTimer = null;
  let teaserDelaySeconds = 3;
  let teaserEnabled = true;

  // Menu state
  let menuItems = null; // Array of {name, description, price, category} or null
  let businessType = ""; // e.g. "legal", "restaurant", "dental"

  // Pre-chat form state
  let preChatForm = null; // array of {name, label, type, required} or null
  let preChatCompleted = false;

  // Booking state
  let tenantId = "";
  let bookingEnabled = false;
  let bookingStep = null; // null | "date" | "slots" | "form" | "confirmed"
  let selectedDate = null;
  let availableSlots = [];
  let selectedSlot = null;
  let bookingMaxDays = 30;
  let tenantPlan = "free";

  // --- API calls ---
  async function fetchConfig() {
    try {
      const resp = await fetchWithTimeout(
        `${API_BASE}/api/v1/widget/config/${encodeURIComponent(API_KEY)}`,
      );
      if (!resp.ok) return;
      const data = await resp.json();
      botName = data.bot_name || "Aria";
      agentName = data.agent_name || "Agent";
      tenantId = data.tenant_id || "";
      bookingEnabled = data.booking_enabled || false;
      businessType = (data.business_type || "").toLowerCase();
      widgetIsOnline = data.is_online !== false;
      if (data.greeting_message) greetingMessage = data.greeting_message;
      if (data.offline_message) offlineMessage = data.offline_message;
      if (data.teaser_message) teaserMessage = data.teaser_message;
      if (data.teaser_delay_seconds !== undefined)
        teaserDelaySeconds = data.teaser_delay_seconds;
      if (data.teaser_enabled !== undefined)
        teaserEnabled = data.teaser_enabled;
      if (data.plan) tenantPlan = data.plan;
      if (data.menu_items && data.menu_items.length > 0) {
        menuItems = data.menu_items;
      }
      if (Array.isArray(data.pre_chat_form) && data.pre_chat_form.length > 0) {
        preChatForm = data.pre_chat_form;
      }
    } catch (e) {
      console.warn("AgentNexLiFy: Failed to fetch config", e);
    }
  }

  async function fetchHistory() {
    // History is loaded from localStorage session; no dedicated history endpoint
    return [];
  }

  async function sendFeedback(messageIndex, rating) {
    if (!API_KEY || !API_BASE) return;
    try {
      await fetchWithTimeout(`${API_BASE}/api/v1/widget/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: API_KEY,
          session_id: getSessionId(),
          message_index: messageIndex,
          rating: rating,
        }),
      });
    } catch (e) {
      // Feedback is best-effort, don't interrupt the user
    }
  }

  const FETCH_TIMEOUT_MS = 15000; // 15 seconds

  async function fetchWithTimeout(
    url,
    options = {},
    timeout = FETCH_TIMEOUT_MS,
  ) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(id);
    }
  }

  async function sendMessage(text) {
    if (!API_KEY || !API_BASE) {
      throw new Error(
        "Widget not configured: missing data-api-key or data-api-base",
      );
    }
    const resp = await fetchWithTimeout(`${API_BASE}/api/v1/widget/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: API_KEY,
        session_id: getSessionId(),
        message: text,
        content_mode: contentMode,
      }),
    });
    if (!resp.ok) {
      const err = await resp.text().catch(() => "");
      throw new Error(`HTTP ${resp.status}: ${err}`);
    }
    return resp.json();
  }

  // --- File upload ---
  async function uploadFile(file) {
    if (!API_KEY || !API_BASE) {
      throw new Error("Widget not configured");
    }
    if (file.size > 5 * 1024 * 1024) {
      throw new Error("File too large (max 5 MB)");
    }
    const formData = new FormData();
    formData.append("file", file);
    formData.append("api_key", API_KEY);
    formData.append("session_id", getSessionId());
    const resp = await fetchWithTimeout(`${API_BASE}/api/v1/widget/upload`, {
      method: "POST",
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.text().catch(() => "");
      throw new Error(`Upload failed: ${err}`);
    }
    return resp.json();
  }

  // --- Menu panel ---
  function toggleMenuPanel() {
    const panel = document.getElementById("anx-menu-panel");
    if (!panel) return;
    if (panel.style.display === "none") {
      renderMenuPanel();
      panel.style.display = "block";
      // Hide booking panel if open
      const bookingPanel = document.getElementById("anx-booking");
      if (bookingPanel) bookingPanel.style.display = "none";
    } else {
      panel.style.display = "none";
    }
  }

  function renderMenuPanel() {
    const panel = document.getElementById("anx-menu-panel");
    if (!panel || !menuItems) return;

    // Group by category
    const categories = {};
    for (const item of menuItems) {
      const cat = item.category || "Menu";
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(item);
    }

    let html = "";
    for (const [cat, items] of Object.entries(categories)) {
      html += `<div class="anx-menu-cat">${_esc(cat)}</div>`;
      for (const item of items) {
        const price = "$" + parseFloat(item.price || 0).toFixed(2);
        html += `<div class="anx-menu-item">`;
        html += `<div><div class="anx-menu-item-name">${_esc(item.name)}</div>`;
        if (item.description) {
          html += `<div class="anx-menu-item-desc">${_esc(item.description)}</div>`;
        }
        html += `</div>`;
        html += `<div class="anx-menu-item-price">${price}</div>`;
        html += `</div>`;
      }
    }
    html += `<div class="anx-menu-order-hint">${t('menuOrderHint')}</div>`;
    panel.innerHTML = html;
  }

  function _esc(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  function _inlineMd(s) {
    // Escape HTML entities first to prevent XSS
    s = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    // Bold **text**
    s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
    // Italic *text* (only when not inside bold)
    s = s.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>");
    // Links [text](url) - only https?:// to prevent XSS
    s = s.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    );
    return s;
  }

  function _renderMd(text) {
    const lines = (text || "").split("\n");
    const out = [];
    let inList = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      if (
        trimmed.startsWith("- ") ||
        trimmed.startsWith("* ") ||
        /^\d+\.\s/.test(trimmed)
      ) {
        if (!inList) {
          out.push('<ul style="margin:4px 0;padding-left:18px;">');
          inList = true;
        }
        const content = trimmed.replace(/^[-*]\s|^\d+\.\s/, "");
        out.push("<li>" + _inlineMd(content) + "</li>");
      } else {
        if (inList) {
          out.push("</ul>");
          inList = false;
        }
        if (trimmed === "") {
          // Skip empty lines at start/end, convert internal empty lines to spacing
          if (out.length > 0 && out[out.length - 1] !== "<br>")
            out.push("<br>");
        } else {
          out.push(_inlineMd(line));
          // Add line break after non-empty lines (except before list items)
          const nextTrimmed = (lines[i + 1] || "").trim();
          if (
            nextTrimmed &&
            !nextTrimmed.startsWith("- ") &&
            !nextTrimmed.startsWith("* ") &&
            !/^\d+\.\s/.test(nextTrimmed)
          ) {
            out.push("<br>");
          }
        }
      }
    }
    if (inList) out.push("</ul>");
    // Remove trailing <br>
    while (out.length && out[out.length - 1] === "<br>") out.pop();
    return out.join("");
  }

  // --- DOM helpers ---
  function addMessage(role, text, attachment) {
    const container = document.getElementById("anx-messages");
    const div = document.createElement("div");
    div.className = `anx-msg ${role}`;

    if (attachment) {
      if (
        attachment.content_type &&
        attachment.content_type.startsWith("image/")
      ) {
        const img = document.createElement("img");
        img.src = attachment.url;
        img.alt = attachment.filename || "Image";
        img.className = "anx-attachment";
        img.onclick = () => window.open(attachment.url, "_blank");
        div.appendChild(img);
      } else {
        const link = document.createElement("a");
        link.href = attachment.url;
        link.target = "_blank";
        link.rel = "noopener";
        link.className = "anx-file-link";
        link.textContent = attachment.filename || "File";
        div.appendChild(link);
      }
      if (text) {
        const p = document.createElement("div");
        p.textContent = text;
        p.style.marginTop = "4px";
        div.appendChild(p);
      }
    } else {
      if (role === "assistant") {
        div.innerHTML = _renderMd(text);
      } else {
        div.textContent = text;
      }
    }

    // Feedback buttons on assistant messages
    const currentIndex = msgCounter++;
    if (role === "assistant" && text) {
      const fbRow = document.createElement("div");
      fbRow.className = "anx-feedback-row";
      fbRow.style.cssText = "display:flex;gap:4px;margin-top:4px;";

      const makeBtn = (label, rating) => {
        const btn = document.createElement("button");
        btn.textContent = label;
        btn.className = "anx-fb-btn";
        btn.style.cssText =
          "background:none;border:none;cursor:pointer;font-size:14px;padding:2px 4px;opacity:0.5;transition:opacity 0.2s;";
        btn.onmouseenter = () => {
          btn.style.opacity = "1";
        };
        btn.onmouseleave = () => {
          if (!btn.dataset.selected) btn.style.opacity = "0.5";
        };
        btn.onclick = () => {
          fbRow.querySelectorAll(".anx-fb-btn").forEach((b) => {
            b.dataset.selected = "";
            b.style.opacity = "0.5";
          });
          btn.dataset.selected = "1";
          btn.style.opacity = "1";
          sendFeedback(currentIndex, rating);
        };
        return btn;
      };

      fbRow.appendChild(makeBtn("\u{1F44D}", "thumbs_up"));
      fbRow.appendChild(makeBtn("\u{1F44E}", "thumbs_down"));
      div.appendChild(fbRow);
    }

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
      btn.href =
        API_BASE.replace(/\/api.*$/, "").replace(/:\d+$/, "") + "/pricing";
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
    if (title) title.textContent = botName;
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
      const badge = document.getElementById("anx-badge");
      if (badge) badge.style.display = "none";
      const input = document.getElementById("anx-input");
      if (input) input.focus();
      localStorage.setItem(STATE_KEY, "open");
      const msgs = document.getElementById("anx-messages");
      if (msgs && msgs.children.length === 0) triggerGreeting();
      hideTeaser();
      if (teaserTimer) {
        clearTimeout(teaserTimer);
        teaserTimer = null;
      }
    } else {
      win.classList.remove("open");
      bubble.classList.remove("hidden");
      localStorage.setItem(STATE_KEY, "closed");
    }
  }

  function showTeaser() {
    const teaser = document.getElementById("anx-teaser");
    if (!teaser || isOpen) return;
    if (sessionStorage.getItem("anx_teaser_shown")) return;

    if (!teaserMessage) return;
    const textEl = document.getElementById("anx-teaser-text");
    if (textEl) textEl.textContent = teaserMessage;

    sessionStorage.setItem("anx_teaser_shown", "1");
    teaser.style.display = "block";

    document.getElementById("anx-teaser-close").onclick = function (e) {
      e.stopPropagation();
      teaser.style.display = "none";
    };

    teaser.onclick = function (e) {
      if (e.target.id === "anx-teaser-close") return;
      teaser.style.display = "none";
      toggleWindow(true);
    };
  }

  function hideTeaser() {
    const teaser = document.getElementById("anx-teaser");
    if (teaser) teaser.style.display = "none";
  }

  async function handleSend() {
    const input = document.getElementById("anx-input");
    const text = input?.value.trim();
    if (!text || isLoading) return;

    // Booking intent detection
    if (
      bookingEnabled &&
      tenantId &&
      /\b(book|appointment|schedule|available|booking)\b/i.test(text)
    ) {
      input.value = "";
      input.style.height = "auto";
      addMessage("user", text);
      addMessage("assistant", t('bookingIntentResponse'));
      setTimeout(() => showBooking("date"), 500);
      return;
    }

    input.value = "";
    input.style.height = "auto";
    addMessage("user", text);

    isLoading = true;
    const sendBtn = document.getElementById("anx-send");
    if (sendBtn) sendBtn.disabled = true;
    showTyping();

    try {
      const data = await sendMessage(text);
      hideTyping();
      addMessage("assistant", data.response);

      // Handle handoff to team member
      if (data.handoff) {
        const inputEl = document.getElementById("anx-input");
        if (inputEl) inputEl.placeholder = t('teamMemberWillRespond');
      }

      // Handle trial expiry
      if (data.trial_expired) {
        disableWidgetInput(t('trialExpired'));
      }
    } catch (e) {
      hideTyping();
      addMessage("assistant", t('connectError'));
      console.error("AgentNexLiFy: Send failed", e);
    } finally {
      isLoading = false;
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  // --- File upload handler ---
  async function handleFileUpload() {
    const fileInput = document.getElementById("anx-file-input");
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    fileInput.value = ""; // Reset so same file can be selected again

    if (file.size > 5 * 1024 * 1024) {
      addMessage(
        "assistant",
        "File is too large. Please send files under 5 MB.",
      );
      return;
    }

    // Show uploading state
    addMessage("user", `Uploading ${file.name}...`);
    const msgs = document.getElementById("anx-messages");
    const uploadingMsg = msgs.lastChild;

    try {
      const result = await uploadFile(file);

      // Replace uploading message with actual attachment
      msgs.removeChild(uploadingMsg);
      addMessage("user", "", result);

      // Send a chat message referencing the attachment so the AI knows about it
      isLoading = true;
      document.getElementById("anx-send").disabled = true;
      showTyping();

      const data = await sendMessage(
        `[Attached file: ${result.filename}] ${result.url}`,
      );
      hideTyping();
      addMessage("assistant", data.response);

      if (data.trial_expired) {
        disableWidgetInput("Your free trial has expired.");
      }
    } catch (e) {
      if (uploadingMsg.parentNode) msgs.removeChild(uploadingMsg);
      hideTyping();
      addMessage(
        "assistant",
        "Sorry, I couldn't upload that file. Please try again.",
      );
      console.error("AgentNexLiFy: File upload failed", e);
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
    const monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDow = new Date(year, month, 1).getDay();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const maxDate = new Date(today);
    maxDate.setDate(maxDate.getDate() + bookingMaxDays);

    let html = `<button class="anx-booking-back" onclick="document.getElementById('anx-booking').__anxBack()">&#8592; Back to chat</button>`;
    html += `<div class="anx-booking-title">Select a Date</div>`;
    html += `<div class="anx-cal-header">`;
    html += `<button class="anx-cal-nav" data-dir="-1">&#8249;</button>`;
    html += `<span>${monthNames[month]} ${year}</span>`;
    html += `<button class="anx-cal-nav" data-dir="1">&#8250;</button>`;
    html += `</div>`;
    html += `<div class="anx-cal-grid">`;
    ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].forEach((d) => {
      html += `<div class="anx-cal-dow">${d}</div>`;
    });
    for (let i = 0; i < firstDow; i++)
      html += `<button class="anx-cal-day empty"></button>`;
    for (let d = 1; d <= daysInMonth; d++) {
      const dt = new Date(year, month, d);
      const isPast = dt < today;
      const isBeyond = dt > maxDate;
      const isToday = dt.getTime() === today.getTime();
      const isSel =
        selectedDate &&
        dt.toDateString() === new Date(selectedDate).toDateString();
      let cls = "anx-cal-day";
      if (isPast || isBeyond) cls += " disabled";
      if (isToday) cls += " today";
      if (isSel) cls += " selected";
      html += `<button class="${cls}" data-date="${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}">${d}</button>`;
    }
    html += `</div>`;

    booking.innerHTML = html;

    // Back to chat
    booking.__anxBack = () => showBooking(null);

    // Month nav
    booking.querySelectorAll(".anx-cal-nav").forEach((btn) => {
      btn.addEventListener("click", () => {
        const dir = parseInt(btn.dataset.dir);
        const nv = new Date(year, month + dir, 1);
        selectedDate = nv.toISOString().split("T")[0];
        renderDatePicker();
      });
    });

    // Day selection
    booking
      .querySelectorAll(".anx-cal-day:not(.disabled):not(.empty)")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          selectedDate = btn.dataset.date;
          showBooking("slots");
        });
      });
  }

  async function renderSlots() {
    const booking = document.getElementById("anx-booking");
    booking.innerHTML = `<button class="anx-booking-back" onclick="document.getElementById('anx-booking').__anxBack()">&#8592; Back</button><div class="anx-booking-title">Available Times</div><div class="anx-slots-empty">Loading...</div>`;
    booking.__anxBack = () => {
      showBooking("date");
    };

    try {
      const resp = await fetchWithTimeout(
        `${API_BASE}/api/v1/appointments/slots/${tenantId}?date=${selectedDate}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: API_KEY }),
        },
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
        html += `<button class="anx-slot-btn" data-idx="${i}">${_esc(slot.start)}</button>`;
      });
      html += `</div>`;
    }

    booking.innerHTML = html;
    booking.__anxBack = () => {
      showBooking("date");
    };

    booking.querySelectorAll(".anx-slot-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedSlot = availableSlots[parseInt(btn.dataset.idx)];
        booking
          .querySelectorAll(".anx-slot-btn")
          .forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        setTimeout(() => showBooking("form"), 300);
      });
    });
  }

  function renderContactForm() {
    const booking = document.getElementById("anx-booking");
    let html = `<button class="anx-booking-back" onclick="document.getElementById('anx-booking').__anxBack()">&#8592; Back</button>`;
    html += `<div class="anx-booking-title">Your Details</div>`;
    html += `<div style="text-align:center;font-size:12px;color:rgba(255,255,255,0.4);margin-bottom:4px;">${_esc(formatBookingDate(selectedDate))} at ${_esc(selectedSlot.start)}</div>`;
    html += `<div class="anx-form-group"><label class="anx-form-label">Name *</label><input class="anx-form-input" id="anx-book-name" placeholder="Your name" required></div>`;
    html += `<div class="anx-form-group"><label class="anx-form-label">Email *</label><input class="anx-form-input" id="anx-book-email" type="email" placeholder="your@email.com" required></div>`;
    html += `<div class="anx-form-group"><label class="anx-form-label">Phone</label><input class="anx-form-input" id="anx-book-phone" type="tel" placeholder="(optional)"></div>`;
    const reasonPlaceholder =
      {
        legal: "e.g. Initial Consultation, Case Review, Document Review",
        dental: "e.g. Cleaning, Checkup, Consultation",
        medical: "e.g. Annual Physical, Follow-up, Consultation",
        salon: "e.g. Haircut, Coloring, Styling",
        restaurant: "e.g. Reservation, Private Event",
        contractor: "e.g. Estimate, Inspection, Repair",
      }[businessType] || "e.g. Consultation, Service, Follow-up";
    html += `<div class="anx-form-group"><label class="anx-form-label">Reason for Visit</label><input class="anx-form-input" id="anx-book-reason" placeholder="${reasonPlaceholder}"></div>`;
    html += `<div class="anx-form-group"><label class="anx-form-label">Notes</label><input class="anx-form-input" id="anx-book-notes" placeholder="(optional)"></div>`;
    html += `<button class="anx-book-submit" id="anx-book-confirm">Confirm Appointment</button>`;
    html += `<div id="anx-book-error" style="color:#ff4444;font-size:12px;text-align:center;display:none;"></div>`;

    booking.innerHTML = html;
    booking.__anxBack = () => {
      showBooking("slots");
    };

    document
      .getElementById("anx-book-confirm")
      .addEventListener("click", submitBooking);
  }

  async function submitBooking() {
    const name = document.getElementById("anx-book-name").value.trim();
    const email = document.getElementById("anx-book-email").value.trim();
    const phone = document.getElementById("anx-book-phone").value.trim();
    const reason = document.getElementById("anx-book-reason").value.trim();
    const rawNotes = document.getElementById("anx-book-notes").value.trim();
    const notes = [reason ? `Service: ${reason}` : "", rawNotes]
      .filter(Boolean)
      .join(" | ");
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
      const resp = await fetchWithTimeout(
        `${API_BASE}/api/v1/appointments/${tenantId}`,
        {
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
        },
      );

      if (resp.status === 409) {
        errEl.textContent =
          "This slot was just taken. Please select another time.";
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
    html += `<div class="anx-confirm-detail">${_esc(formatBookingDate(selectedDate))} at ${_esc(selectedSlot.start)}</div>`;
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
    return d.toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  // --- Offline Mode ---
  function showOfflineForm() {
    const messages = document.getElementById("anx-messages");
    const inputArea = document.getElementById("anx-input-area");
    const booking = document.getElementById("anx-booking");
    if (messages) messages.style.display = "none";
    if (inputArea) inputArea.style.display = "none";
    if (booking) booking.style.display = "none";

    // Create offline form container
    let form = document.getElementById("anx-offline-form");
    if (!form) {
      form = document.createElement("div");
      form.id = "anx-offline-form";
      const win = document.getElementById("anx-window");
      const powered = document.getElementById("anx-powered");
      win.insertBefore(form, powered);
    }

    form.innerHTML = `
      <div class="anx-offline-msg">${_esc(offlineMessage)}</div>
      <div class="anx-form-group">
        <label class="anx-form-label">Name *</label>
        <input class="anx-form-input" id="anx-offline-name" placeholder="Your name" required>
      </div>
      <div class="anx-form-group">
        <label class="anx-form-label">Email *</label>
        <input class="anx-form-input" id="anx-offline-email" type="email" placeholder="your@email.com" required>
      </div>
      <div class="anx-form-group">
        <label class="anx-form-label">Phone</label>
        <input class="anx-form-input" id="anx-offline-phone" type="tel" placeholder="(optional)">
      </div>
      <div class="anx-form-group">
        <label class="anx-form-label">Message *</label>
        <textarea class="anx-form-input" id="anx-offline-message" placeholder="How can we help you?" rows="3" style="resize:none;"></textarea>
      </div>
      <button class="anx-book-submit" id="anx-offline-submit">Send Message</button>
      <div id="anx-offline-error" style="color:#ff4444;font-size:12px;text-align:center;display:none;"></div>
    `;
    form.style.display = "flex";

    document
      .getElementById("anx-offline-submit")
      .addEventListener("click", submitOfflineForm);
  }

  async function submitOfflineForm() {
    const name = document.getElementById("anx-offline-name").value.trim();
    const email = document.getElementById("anx-offline-email").value.trim();
    const phone = document.getElementById("anx-offline-phone").value.trim();
    const message = document.getElementById("anx-offline-message").value.trim();
    const errEl = document.getElementById("anx-offline-error");
    const btn = document.getElementById("anx-offline-submit");

    if (!name || !email || !message) {
      errEl.textContent = "Name, email, and message are required.";
      errEl.style.display = "block";
      return;
    }

    btn.disabled = true;
    btn.textContent = "Sending...";
    errEl.style.display = "none";

    try {
      const resp = await fetchWithTimeout(
        `${API_BASE}/api/v1/widget/offline-contact`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            api_key: API_KEY,
            name,
            email,
            phone: phone || null,
            message,
          }),
        },
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      // Show success
      const form = document.getElementById("anx-offline-form");
      form.innerHTML = `
        <div class="anx-offline-success">
          <div class="anx-offline-success-icon">&#10003;</div>
          <div class="anx-confirm-title">Message Sent!</div>
          <div class="anx-confirm-detail" style="margin-top:8px;">Thank you, ${_esc(name)}. We'll get back to you soon.</div>
          <button class="anx-confirm-back" id="anx-offline-reset" style="margin-top:16px;">Send Another Message</button>
        </div>
      `;
      document
        .getElementById("anx-offline-reset")
        .addEventListener("click", showOfflineForm);
    } catch (e) {
      console.error("AgentNexLiFy: Offline form submit failed", e);
      errEl.textContent = "Something went wrong. Please try again.";
      errEl.style.display = "block";
      btn.disabled = false;
      btn.textContent = "Send Message";
    }
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

    // Offline mode - show contact form instead of chat
    if (!widgetIsOnline) {
      const statusEl = document.querySelector("#anx-header-text p");
      if (statusEl)
        statusEl.innerHTML =
          '<span class="anx-header-status" style="background:#ef4444;"></span>Currently offline';
      showOfflineForm();
      // Still wire up open/close
      document
        .getElementById("anx-bubble")
        .addEventListener("click", () => toggleWindow(true));
      document
        .getElementById("anx-minimize")
        .addEventListener("click", () => toggleWindow(false));
      document
        .getElementById("anx-close")
        .addEventListener("click", () => toggleWindow(false));
      // Auto-open after 5s
      const savedState = localStorage.getItem(STATE_KEY);
      if (savedState === "open") toggleWindow(true);
      else if (savedState !== "closed") {
        setTimeout(() => {
          if (!isOpen && !hasAutoOpened) {
            hasAutoOpened = true;
            toggleWindow(true);
          }
        }, 5000);
      }
      return; // Skip chat setup
    }

    // Show menu button if menu items available
    if (menuItems && menuItems.length > 0) {
      const menuBtn = document.getElementById("anx-menu-btn");
      if (menuBtn) {
        menuBtn.style.display = "flex";
        menuBtn.addEventListener("click", toggleMenuPanel);
      }
    }

    // Show booking button if enabled
    if (bookingEnabled && tenantId) {
      const bookBtn = document.getElementById("anx-booking-btn");
      if (bookBtn) {
        bookBtn.style.display = "flex";
        bookBtn.addEventListener("click", () => showBooking("date"));
      }
    }

    // Show content mode button for professional+ plans
    const _plan = tenantPlan;
    if (_plan === "professional" || _plan === "enterprise") {
      const cmBtn = document.getElementById("anx-content-mode-btn");
      if (cmBtn) {
        cmBtn.style.display = "flex";
        cmBtn.addEventListener("click", function () {
          contentMode = !contentMode;
          cmBtn.classList.toggle("active", contentMode);
          const badge = document.getElementById("anx-content-mode-badge");
          if (badge) badge.style.display = contentMode ? "block" : "none";
          const input = document.getElementById("anx-input");
          if (input)
            input.placeholder = contentMode
              ? "Paste content, URL, or YouTube link to repurpose..."
              : "Type a message...";
        });
      }
    }

    // Load existing history
    const history = await fetchHistory();
    for (const msg of history) {
      if (msg.role === "user" || msg.role === "assistant") {
        addMessage(msg.role, msg.content);
      }
    }

    // Show pre-chat form if configured and no history
    if (history.length === 0 && !showPreChatForm()) {
      triggerGreeting();
    } else if (history.length > 0) {
      // History exists, mark pre-chat as done
      preChatCompleted = true;
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
    document.getElementById("anx-send").addEventListener("click", handleSend);

    // File attachment
    document
      .getElementById("anx-attach")
      .addEventListener("click", () =>
        document.getElementById("anx-file-input").click(),
      );
    document
      .getElementById("anx-file-input")
      .addEventListener("change", handleFileUpload);

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
        }
      }, 5000);
    }

    // Show teaser bubble after configured delay if enabled, widget is closed, not yet shown this session,
    // and a teaser_message has been configured.
    if (
      teaserEnabled &&
      teaserMessage &&
      !sessionStorage.getItem("anx_teaser_shown")
    ) {
      teaserTimer = setTimeout(showTeaser, teaserDelaySeconds * 1000);
    }
  }

  function showPreChatForm() {
    if (!preChatForm || preChatForm.length === 0 || preChatCompleted)
      return false;
    // Skip if already filled this session
    if (sessionStorage.getItem("anx_prechat_done")) {
      preChatCompleted = true;
      return false;
    }
    const msgs = document.getElementById("anx-messages");
    if (!msgs) return false;

    const formDiv = document.createElement("div");
    formDiv.id = "anx-prechat-form";
    formDiv.style.cssText = "padding:16px;";

    const title = document.createElement("div");
    title.style.cssText =
      "font-weight:600;font-size:0.95rem;margin-bottom:12px;color:#e2e8f0;";
    title.textContent = "Before we start, tell us a bit about yourself:";
    formDiv.appendChild(title);

    preChatForm.forEach(function (field) {
      const wrapper = document.createElement("div");
      wrapper.style.cssText = "margin-bottom:10px;";
      const label = document.createElement("label");
      label.style.cssText =
        "display:block;font-size:0.8rem;color:#94a3b8;margin-bottom:4px;";
      label.textContent = field.label + (field.required ? " *" : "");
      wrapper.appendChild(label);
      const input = document.createElement("input");
      input.type = field.type === "phone" ? "tel" : field.type || "text";
      input.name = field.name || field.label.toLowerCase().replace(/\s+/g, "_");
      input.required = field.required || false;
      input.placeholder = field.label;
      input.style.cssText =
        "width:100%;padding:8px 10px;border-radius:6px;border:1px solid rgba(255,255,255,0.15);background:rgba(255,255,255,0.07);color:#e2e8f0;font-size:0.85rem;box-sizing:border-box;outline:none;";
      wrapper.appendChild(input);
      formDiv.appendChild(wrapper);
    });

    const btn = document.createElement("button");
    btn.textContent = "Start Chat";
    btn.style.cssText =
      "width:100%;padding:10px;border:none;border-radius:8px;background:" +
      (document.getElementById("anx-header")?.style.background || "#6366f1") +
      ";color:#fff;font-weight:600;cursor:pointer;font-size:0.9rem;margin-top:4px;";
    btn.addEventListener("click", function () {
      // Validate required fields
      var inputs = formDiv.querySelectorAll("input");
      var data = {};
      var valid = true;
      inputs.forEach(function (inp) {
        if (inp.required && !inp.value.trim()) {
          inp.style.borderColor = "#f87171";
          valid = false;
        } else {
          inp.style.borderColor = "rgba(255,255,255,0.15)";
        }
        data[inp.name] = inp.value.trim();
      });
      if (!valid) return;

      // Store in session and visitor_info
      sessionStorage.setItem("anx_prechat_done", "1");
      sessionStorage.setItem("anx_prechat_data", JSON.stringify(data));
      preChatCompleted = true;

      // If name/email captured, pre-populate for lead capture
      if (data.name) sessionStorage.setItem("anx_visitor_name", data.name);
      if (data.email) sessionStorage.setItem("anx_visitor_email", data.email);
      if (data.phone) sessionStorage.setItem("anx_visitor_phone", data.phone);

      // Remove form and show greeting
      formDiv.remove();
      triggerGreeting();

      // Enable input
      var inputEl = document.getElementById("anx-input");
      if (inputEl) {
        inputEl.disabled = false;
        inputEl.focus();
      }
      var sendEl = document.getElementById("anx-send");
      if (sendEl) sendEl.disabled = false;
    });
    formDiv.appendChild(btn);

    msgs.appendChild(formDiv);

    // Disable chat input while form is shown
    var inputEl = document.getElementById("anx-input");
    if (inputEl) {
      inputEl.disabled = true;
      inputEl.placeholder = "Fill out the form above to start chatting...";
    }
    var sendEl = document.getElementById("anx-send");
    if (sendEl) sendEl.disabled = true;

    return true;
  }

  function triggerGreeting() {
    const msgs = document.getElementById("anx-messages");
    if (!msgs || msgs.children.length > 0) return;
    const rawGreeting =
      greetingMessage || "How can I help you today?";
    const greetingWithDisclosure = /\bAI\b/i.test(rawGreeting)
      ? rawGreeting
      : `Hi! I'm the AI assistant for this business. ${rawGreeting}`;
    addMessage(
      "assistant",
      greetingWithDisclosure,
    );
  }

  // --- Run ---
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
