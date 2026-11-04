/**
 * First visit to Agent OS: ask the business type, then offer 5-8 one-click
 * recurring tasks. Clicking one creates the scheduled task. It does not send
 * anything to a customer.
 */
import { useState } from "react";
import { createOsTask } from "../../utils/api/os";
import { updateTenantSettings } from "../../utils/api/dashboard";
import {
  BUSINESS_TYPES,
  resolveBusinessType,
  templatesFor,
} from "./starterTemplates";

export default function GuidedSetup({
  businessType,
  tenantId,
  token,
  isMobile,
}) {
  const preset = resolveBusinessType(businessType);
  const [chosen, setChosen] = useState(preset);
  const [asking, setAsking] = useState(!preset);
  const [added, setAdded] = useState({});
  const [busyKey, setBusyKey] = useState("");
  const [error, setError] = useState("");

  const templates = templatesFor(chosen || "other");

  async function pickType(id) {
    setChosen(id);
    setAsking(false);
    setError("");
    if (token && tenantId) {
      try {
        await updateTenantSettings(tenantId, token, { business_type: id });
      } catch (err) {
        setError(
          err?.message ||
            "Saved your choice here. Business settings did not update.",
        );
      }
    }
  }

  async function addTask(item) {
    if (!token) return;
    setBusyKey(item.label);
    setError("");
    try {
      await createOsTask(token, {
        department: item.department,
        prompt: item.prompt,
        interval_days: item.interval_days,
        enabled: true,
      });
      setAdded((prev) => ({ ...prev, [item.label]: true }));
    } catch (err) {
      setError(err?.message || "Could not add that task.");
    } finally {
      setBusyKey("");
    }
  }

  return (
    <div
      style={{
        height: "100%",
        overflowY: "auto",
        padding: isMobile ? "24px 16px" : "32px 24px",
      }}
    >
      <div style={{ maxWidth: 640, margin: "0 auto" }}>
        <div
          style={{
            fontSize: isMobile ? "1rem" : "1.15rem",
            fontWeight: 650,
            color: "var(--text-primary)",
            marginBottom: 6,
          }}
        >
          Set up your AI staff
        </div>
        <div
          style={{
            fontSize: "0.85rem",
            color: "var(--text-muted)",
            lineHeight: 1.55,
            marginBottom: 18,
          }}
        >
          {asking
            ? "What kind of business is this? Then you can turn on a few ready-made tasks. Each one drafts work for you to review. Nothing sends on its own."
            : "Turn on the tasks you want. Each one drafts work on a schedule for you to review. Nothing sends on its own."}
        </div>

        {asking ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
              gap: 10,
            }}
          >
            {BUSINESS_TYPES.map((type) => (
              <button
                key={type.id}
                type="button"
                onClick={() => pickType(type.id)}
                style={choiceStyle}
              >
                {type.label}
              </button>
            ))}
          </div>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
                gap: 8,
              }}
            >
              <div
                style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}
              >
                {
                  BUSINESS_TYPES.find((t) => t.id === (chosen || "other"))
                    ?.label
                }
              </div>
              <button
                type="button"
                onClick={() => setAsking(true)}
                style={quietBtn}
              >
                Change business type
              </button>
            </div>
            <div style={{ display: "grid", gap: 10 }}>
              {templates.map((item) => {
                const done = Boolean(added[item.label]);
                return (
                  <div
                    key={item.label}
                    style={{
                      border: "1px solid var(--border)",
                      borderRadius: 10,
                      padding: "12px 14px",
                      background: "var(--bg-secondary)",
                      display: "flex",
                      gap: 12,
                      alignItems: "center",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: "0.88rem",
                          fontWeight: 600,
                          color: "var(--text-primary)",
                        }}
                      >
                        {item.label}
                      </div>
                      <div
                        style={{
                          fontSize: "0.78rem",
                          color: "var(--text-muted)",
                          marginTop: 3,
                          lineHeight: 1.45,
                        }}
                      >
                        {item.blurb} Every {item.interval_days} day
                        {item.interval_days === 1 ? "" : "s"}.
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={done || busyKey === item.label}
                      onClick={() => addTask(item)}
                      style={{
                        ...quietBtn,
                        background: done
                          ? "transparent"
                          : "var(--accent, #6366f1)",
                        color: done ? "var(--text-muted)" : "#fff",
                        border: done ? "1px solid var(--border)" : "none",
                        minWidth: 72,
                      }}
                    >
                      {done
                        ? "Added"
                        : busyKey === item.label
                          ? "Adding..."
                          : "Add"}
                    </button>
                  </div>
                );
              })}
            </div>
          </>
        )}
        {error && (
          <div style={{ color: "#f87171", fontSize: "0.8rem", marginTop: 12 }}>
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

const choiceStyle = {
  background: "var(--bg-secondary)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  padding: "12px 14px",
  fontSize: "0.85rem",
  color: "var(--text-secondary)",
  cursor: "pointer",
  textAlign: "left",
};

const quietBtn = {
  border: "1px solid var(--border)",
  background: "transparent",
  color: "var(--text-secondary)",
  borderRadius: 8,
  padding: "6px 10px",
  fontSize: "0.78rem",
  cursor: "pointer",
};
