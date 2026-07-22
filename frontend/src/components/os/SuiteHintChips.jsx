/**
 * SuiteHintChips - thin chip row above the workforce composer that teaches
 * the chat fast paths by pre-filling them (round-5 item 3). The typed
 * shortcuts (deterministic BI answers, chat-queued projects) shipped with
 * zero discoverability - owners cannot use phrasings they have never seen.
 * Clicking a chip populates the composer and focuses it; nothing sends.
 */

const CHIPS = [
  {
    label: "Ask your data",
    prompt: "How many leads did we get this week?",
    title: "Instant answers computed from your own records",
  },
  {
    label: "Start a project",
    prompt: "Start a project: ",
    title: "One goal becomes a multi-department plan you approve",
  },
  {
    label: "Weekly numbers",
    prompt: "How much revenue did we collect this month?",
    title: "Revenue, bookings, and lead counts - never guessed",
  },
];

export default function SuiteHintChips({ onSelectPrompt, composerRef, disabled }) {
  const pick = (prompt) => {
    if (disabled) return;
    onSelectPrompt(prompt);
    if (composerRef && composerRef.current) {
      composerRef.current.focus();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        gap: 6,
        flexWrap: "wrap",
        padding: "8px 14px 0",
      }}
    >
      {CHIPS.map((chip) => (
        <button
          key={chip.label}
          type="button"
          title={chip.title}
          onClick={() => pick(chip.prompt)}
          disabled={disabled}
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: 999,
            padding: "3px 12px",
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            cursor: disabled ? "default" : "pointer",
          }}
        >
          {chip.label}
        </button>
      ))}
    </div>
  );
}
