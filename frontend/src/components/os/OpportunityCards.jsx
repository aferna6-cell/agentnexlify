/**
 * OpportunityCards - pending proactive suggestions with Accept / Dismiss.
 *
 * The nightly scan files cards like "5 leads went cold this week" into
 * os_backlog_requests. Until this component existed the cards had NO
 * surface at all: the API client functions were exported but never
 * imported by any page, so 12 suggestions sat pending in prod for a month
 * with no way for an owner to act. Accept fires the fulfillment path
 * (drafts land in the approval queue); Dismiss declines the card.
 *
 * Renders nothing when there is nothing to review - this is a prompt, not
 * a dashboard section that needs an empty state.
 */
import { useCallback, useEffect, useState } from "react";
import { listOsBacklog, decideOsBacklog } from "../../utils/api/os";
import { notify } from "../../utils/notify";

const ACTIONABLE = new Set(["pending", "open"]);

const CARD_STYLE = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: "10px",
  padding: "14px 16px",
  marginBottom: "10px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "14px",
};

const BUTTON_BASE = {
  padding: "7px 14px",
  borderRadius: "8px",
  fontSize: "0.8rem",
  fontWeight: 600,
  cursor: "pointer",
};

export default function OpportunityCards({ token }) {
  const [cards, setCards] = useState([]);
  const [busy, setBusy] = useState({});

  useEffect(() => {
    let cancelled = false;
    listOsBacklog(token)
      .then((rows) => {
        if (cancelled) return;
        setCards((rows || []).filter((r) => ACTIONABLE.has(r.status)));
      })
      .catch(() => {
        // Opportunistic surface - a fetch failure just means no cards.
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const decide = useCallback(
    async (id, decision) => {
      setBusy((b) => ({ ...b, [id]: true }));
      try {
        await decideOsBacklog(token, id, { decision });
        setCards((prev) => prev.filter((c) => c.id !== id));
        notify.success(
          decision === "accepted"
            ? "Accepted - your staff is drafting the messages. They'll show up in your approvals."
            : "Dismissed",
        );
      } catch (err) {
        notify.error(err?.message || "Could not save your decision");
      } finally {
        setBusy((b) => ({ ...b, [id]: false }));
      }
    },
    [token],
  );

  if (cards.length === 0) return null;

  return (
    <div style={{ marginBottom: 20 }}>
      <div
        style={{
          color: "var(--text-muted)",
          fontSize: "0.75rem",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 8,
        }}
      >
        Your AI staff spotted {cards.length}{" "}
        {cards.length === 1 ? "opportunity" : "opportunities"}
      </div>
      {cards.map((card) => (
        <div key={card.id} style={CARD_STYLE}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                color: "#fff",
                fontSize: "0.9rem",
                fontWeight: 600,
                marginBottom: 4,
              }}
            >
              {card.summary}
            </div>
            {card.detail && (
              <div
                style={{
                  color: "#9ca3af",
                  fontSize: "0.8rem",
                  lineHeight: 1.5,
                }}
              >
                {card.detail}
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <button
              type="button"
              disabled={Boolean(busy[card.id])}
              onClick={() => decide(card.id, "accepted")}
              style={{
                ...BUTTON_BASE,
                background: "var(--accent, #6366f1)",
                border: "none",
                color: "#fff",
                opacity: busy[card.id] ? 0.6 : 1,
              }}
            >
              Accept
            </button>
            <button
              type="button"
              disabled={Boolean(busy[card.id])}
              onClick={() => decide(card.id, "declined")}
              style={{
                ...BUTTON_BASE,
                background: "transparent",
                border: "1px solid #3a3a4a",
                color: "#9ca3af",
                opacity: busy[card.id] ? 0.6 : 1,
              }}
            >
              Dismiss
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
