/**
 * FirstRunStarters — shown in the empty chat area when a tenant has zero
 * threads (their very first visit to Agent OS). Renders a short welcome line
 * and 3-4 vertical-tailored starter prompts. Clicking one populates the
 * composer textarea and focuses it — it does NOT auto-send.
 *
 * Props:
 *   businessType   {string}  from useAuth().user.businessType (may be empty)
 *   onSelectPrompt {fn}      called with the prompt string; caller sets composer
 *   composerRef    {ref}     forwarded ref to the composer textarea for focus
 *   isMobile       {bool}    from useIsMobile(); adjusts layout
 */

const STARTERS_BY_TYPE = {
  restaurant: [
    "What came in from the widget today?",
    "Follow up with anyone who asked about reservations",
    "What do you know about my menu and popular dishes?",
    "Draft a reminder for tomorrow's bookings",
  ],
  auto: [
    "Follow up on my open quotes",
    "What came in from the widget today?",
    "Draft a reminder for tomorrow's appointments",
    "What do you know about my business so far?",
  ],
  dental: [
    "What came in from the widget today?",
    "Draft a reminder for patients due for a check-up",
    "Follow up on any open treatment plan conversations",
    "What do you know about my practice so far?",
  ],
  medical: [
    "What came in from the widget today?",
    "Draft a recall message for patients not seen in 6 months",
    "Follow up on appointment requests from this week",
    "What do you know about my practice so far?",
  ],
  salon: [
    "What came in from the widget today?",
    "Follow up on open booking requests",
    "Draft a reminder for tomorrow's appointments",
    "What do you know about my salon so far?",
  ],
  // Default for all other business types
  _default: [
    "What came in from the widget today?",
    "Follow up with leads who haven't heard from us",
    "Draft a reminder for tomorrow's appointments",
    "What do you know about my business so far?",
  ],
};

// Marketing + operations live in Agent OS (standalone dashboard pages and the
// marketing add-on were retired 2026-06-10). These starters surface that work
// conversationally for every vertical.
const SHARED_STARTERS = [
  "Plan this week's social media posts",
  "Draft an email campaign for past customers",
  "Send an invoice for a finished job",
  "What's on my calendar this week?",
];

function getStarters(businessType) {
  const key = (businessType || "").toLowerCase();
  // Match on common substrings for types like "auto_shop", "auto repair", etc.
  if (key.includes("restaurant") || key.includes("food") || key.includes("cafe")) return STARTERS_BY_TYPE.restaurant;
  if (key.includes("auto") || key.includes("mechanic") || key.includes("repair")) return STARTERS_BY_TYPE.auto;
  if (key.includes("dental") || key.includes("dentist")) return STARTERS_BY_TYPE.dental;
  if (key.includes("medical") || key.includes("doctor") || key.includes("clinic") || key.includes("health")) return STARTERS_BY_TYPE.medical;
  if (key.includes("salon") || key.includes("spa") || key.includes("beauty") || key.includes("hair")) return STARTERS_BY_TYPE.salon;
  return STARTERS_BY_TYPE._default;
}

export default function FirstRunStarters({ businessType, onSelectPrompt, composerRef, isMobile }) {
  const starters = [...getStarters(businessType), ...SHARED_STARTERS];

  function handleClick(prompt) {
    onSelectPrompt(prompt);
    // Focus the composer so the user can edit or send immediately
    if (composerRef && composerRef.current) {
      composerRef.current.focus();
    }
  }

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: isMobile ? "24px 16px" : "40px 24px",
        gap: 24,
      }}
    >
      <div style={{ textAlign: "center", maxWidth: 480 }}>
        <div
          style={{
            fontSize: isMobile ? "1rem" : "1.1rem",
            fontWeight: 600,
            color: "var(--text-secondary)",
            marginBottom: 8,
          }}
        >
          Hand a task to the orchestrator
        </div>
        <div
          style={{
            fontSize: "0.85rem",
            color: "var(--text-muted)",
            lineHeight: 1.6,
          }}
        >
          Describe what you need. The orchestrator answers directly,
          routes it to a worker agent, or parks it for your decision when
          nothing fits.
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
          gap: 10,
          width: "100%",
          maxWidth: 520,
        }}
      >
        {starters.map((prompt) => (
          <button
            key={prompt}
            onClick={() => handleClick(prompt)}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 10,
              padding: "11px 14px",
              fontSize: "0.82rem",
              lineHeight: 1.4,
              color: "var(--text-secondary)",
              cursor: "pointer",
              textAlign: "left",
              transition: "border-color 0.15s, color 0.15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)";
              e.currentTarget.style.color = "var(--text-primary)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.color = "var(--text-secondary)";
            }}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
