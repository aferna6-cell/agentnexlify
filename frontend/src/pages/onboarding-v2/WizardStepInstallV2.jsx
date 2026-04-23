import { useState } from "react";
import { getWidgetHealth } from "../../utils/api/onboardingV2";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

function CodeBlock({ code }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div style={{ position: "relative" }}>
      <pre
        style={{
          background: "rgba(0,0,0,0.4)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 8,
          padding: "14px 16px",
          fontSize: "0.78rem",
          color: "#a5b4fc",
          overflowX: "auto",
          margin: 0,
          lineHeight: 1.6,
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
        }}
      >
        {code}
      </pre>
      <button
        type="button"
        onClick={handleCopy}
        style={{
          position: "absolute",
          top: 8,
          right: 8,
          padding: "4px 10px",
          minHeight: 28,
          background: copied ? "rgba(34,197,94,0.2)" : "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 6,
          color: copied ? "#4ade80" : "rgba(255,255,255,0.6)",
          fontSize: "0.75rem",
          cursor: "pointer",
          fontWeight: 500,
        }}
      >
        {copied ? "Copied!" : "Copy"}
      </button>
    </div>
  );
}

function Accordion({ title, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      style={{
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 8,
        overflow: "hidden",
        marginTop: 10,
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 16px",
          background: "rgba(255,255,255,0.03)",
          border: "none",
          color: "rgba(255,255,255,0.8)",
          fontSize: "0.9rem",
          fontWeight: 500,
          cursor: "pointer",
          minHeight: 48,
          textAlign: "left",
        }}
      >
        {title}
        <span style={{ color: "rgba(255,255,255,0.35)", fontSize: "0.8rem" }}>
          {open ? "Hide" : "Show"}
        </span>
      </button>
      {open && (
        <div
          style={{
            padding: "14px 16px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            background: "rgba(255,255,255,0.01)",
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}

function HealthStatus({ status }) {
  if (!status) return null;
  const color =
    status.live === true
      ? "#4ade80"
      : status.live === false
        ? "#f87171"
        : "#fbbf24";
  const label =
    status.live === true
      ? "Widget detected"
      : status.live === false
        ? "Widget not found"
        : "Partial";
  const detail = status.message || "";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        padding: "12px 14px",
        background: "rgba(255,255,255,0.03)",
        border: `1px solid ${color}40`,
        borderRadius: 8,
        marginTop: 12,
      }}
    >
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: color,
          flexShrink: 0,
          marginTop: 3,
        }}
      />
      <div>
        <div style={{ fontWeight: 600, fontSize: "0.9rem", color }}>
          {label}
        </div>
        {detail && (
          <div
            style={{
              fontSize: "0.82rem",
              color: "rgba(255,255,255,0.45)",
              marginTop: 2,
            }}
          >
            {detail}
          </div>
        )}
      </div>
    </div>
  );
}

export default function WizardStepInstallV2({
  wizardData,
  token,
  user,
  onComplete,
  onBack,
  completing,
}) {
  const tenantId = user?.tenantId || "";
  const embedSnippet = `<script
  src="${API_BASE}/api/v1/widget/agentnexlify-widget.js"
  data-tenant="${tenantId}"
  async
></script>`;

  const [tab, setTab] = useState("wordpress");
  const [domains, setDomains] = useState(
    wizardData.websiteUrl
      ? [
          wizardData.websiteUrl
            .replace(/^https?:\/\//, "")
            .replace(/\/$/, "")
            .split("/")[0],
        ]
      : [],
  );
  const [domainInput, setDomainInput] = useState("");
  const [healthStatus, setHealthStatus] = useState(null);
  const [checkingHealth, setCheckingHealth] = useState(false);

  function addDomain() {
    const d = domainInput
      .trim()
      .replace(/^https?:\/\//, "")
      .replace(/\/$/, "");
    if (!d || domains.includes(d)) return;
    setDomains((prev) => [...prev, d]);
    setDomainInput("");
  }

  function removeDomain(d) {
    setDomains((prev) => prev.filter((x) => x !== d));
  }

  function handleDomainKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      addDomain();
    }
  }

  async function handleHealthCheck() {
    if (checkingHealth) return;
    const domain =
      domains[0] ||
      wizardData.websiteUrl
        ?.replace(/^https?:\/\//, "")
        .replace(/\/$/, "")
        .split("/")[0];
    if (!domain) {
      setHealthStatus({ live: false, message: "Add a domain above to check." });
      return;
    }
    setCheckingHealth(true);
    setHealthStatus(null);
    try {
      const result = await getWidgetHealth(token, domain);
      setHealthStatus(result);
    } catch {
      setHealthStatus({
        live: false,
        message: "Could not reach the health check endpoint.",
      });
    } finally {
      setCheckingHealth(false);
    }
  }

  return (
    <div>
      <h2 style={headingStyle}>Install your widget</h2>
      <p style={subStyle}>
        Add the widget to your website so customers can chat with your AI
        assistant.
      </p>

      {/* Install method tabs */}
      <div style={tabBarStyle}>
        {[
          { key: "wordpress", label: "WordPress" },
          { key: "script", label: "Script tag" },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            style={{
              flex: 1,
              padding: "10px 0",
              minHeight: 44,
              border: "none",
              borderRadius: 6,
              background:
                tab === t.key ? "rgba(99,102,241,0.25)" : "transparent",
              color: tab === t.key ? "#a5b4fc" : "rgba(255,255,255,0.45)",
              fontWeight: tab === t.key ? 600 : 400,
              fontSize: "0.9rem",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "wordpress" && (
        <div style={tabPanelStyle}>
          <p style={tabDescStyle}>
            Download and install our WordPress plugin — no code required.
          </p>
          <a
            href={`${API_BASE}/api/v1/widget/plugin/download`}
            download
            style={downloadBtnStyle}
          >
            Download WordPress plugin
          </a>
          <Accordion title="How to install (3 steps)">
            <ol
              style={{
                margin: 0,
                padding: "0 0 0 18px",
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
            >
              <li style={stepStyle}>
                Go to your WordPress admin panel and navigate to{" "}
                <strong>Plugins &gt; Add New</strong>.
              </li>
              <li style={stepStyle}>
                Click <strong>Upload Plugin</strong>, choose the downloaded .zip
                file, and click <strong>Install Now</strong>.
              </li>
              <li style={stepStyle}>
                Click <strong>Activate</strong>. The widget appears
                automatically on your site — no configuration needed.
              </li>
            </ol>
          </Accordion>
        </div>
      )}

      {tab === "script" && (
        <div style={tabPanelStyle}>
          <p style={tabDescStyle}>
            Paste this snippet before the closing &lt;/body&gt; tag on every
            page.
          </p>
          <CodeBlock code={embedSnippet} />
        </div>
      )}

      {/* Allowed domains */}
      <div style={sectionStyle}>
        <p style={sectionLabelStyle}>Allowed domains</p>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            marginBottom: 10,
          }}
        >
          {domains.map((d) => (
            <div key={d} style={domainChipStyle}>
              <span style={{ fontSize: "0.82rem" }}>{d}</span>
              <button
                type="button"
                onClick={() => removeDomain(d)}
                aria-label={`Remove ${d}`}
                style={chipRemoveStyle}
              >
                x
              </button>
            </div>
          ))}
          {domains.length === 0 && (
            <span
              style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.3)" }}
            >
              No domains added — widget loads on any domain
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            style={{ ...inputStyle, flex: 1 }}
            value={domainInput}
            onChange={(e) => setDomainInput(e.target.value)}
            onKeyDown={handleDomainKeyDown}
            placeholder="yoursite.com"
            inputMode="url"
          />
          <button
            type="button"
            onClick={addDomain}
            disabled={!domainInput.trim()}
            style={addBtnStyle(!domainInput.trim())}
          >
            Add
          </button>
        </div>
      </div>

      {/* Widget health check */}
      <div style={sectionStyle}>
        <p style={sectionLabelStyle}>Check if widget is live</p>
        <p
          style={{
            fontSize: "0.82rem",
            color: "rgba(255,255,255,0.4)",
            marginTop: 0,
            marginBottom: 12,
          }}
        >
          After installing, use this to confirm the widget loaded correctly.
        </p>
        <button
          type="button"
          onClick={handleHealthCheck}
          disabled={checkingHealth}
          style={healthBtnStyle(checkingHealth)}
        >
          {checkingHealth ? "Checking..." : "Check widget status"}
        </button>
        <HealthStatus status={healthStatus} />
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button type="button" onClick={onBack} style={backBtnStyle}>
          Back
        </button>
        <button
          type="button"
          onClick={() => onComplete({})}
          disabled={completing}
          style={completeBtnStyle(completing)}
        >
          {completing ? "Finishing setup..." : "Complete setup"}
        </button>
      </div>

      <p
        style={{
          textAlign: "center",
          fontSize: "0.8rem",
          color: "rgba(255,255,255,0.3)",
          marginTop: 12,
        }}
      >
        You can install the widget later from your dashboard
      </p>
    </div>
  );
}

const headingStyle = {
  fontSize: "1.4rem",
  fontWeight: 700,
  marginBottom: 8,
  marginTop: 0,
};
const subStyle = {
  color: "rgba(255,255,255,0.5)",
  marginBottom: 20,
  fontSize: "0.9rem",
  marginTop: 0,
};
const tabBarStyle = {
  display: "flex",
  background: "rgba(255,255,255,0.04)",
  borderRadius: 8,
  padding: 3,
  marginBottom: 16,
};
const tabPanelStyle = {
  background: "rgba(255,255,255,0.02)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10,
  padding: "16px",
  marginBottom: 16,
};
const tabDescStyle = {
  fontSize: "0.88rem",
  color: "rgba(255,255,255,0.5)",
  marginTop: 0,
  marginBottom: 14,
};
const downloadBtnStyle = {
  display: "block",
  width: "100%",
  padding: "14px",
  minHeight: 50,
  background: "rgba(99,102,241,0.2)",
  border: "1px solid rgba(99,102,241,0.4)",
  borderRadius: 8,
  color: "#a5b4fc",
  fontWeight: 600,
  fontSize: "0.95rem",
  textAlign: "center",
  textDecoration: "none",
  boxSizing: "border-box",
  marginBottom: 4,
};
const stepStyle = {
  fontSize: "0.88rem",
  color: "rgba(255,255,255,0.65)",
  lineHeight: 1.5,
};
const sectionStyle = {
  background: "rgba(255,255,255,0.02)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10,
  padding: "16px",
  marginBottom: 14,
};
const sectionLabelStyle = {
  fontSize: "0.8rem",
  fontWeight: 600,
  color: "rgba(255,255,255,0.4)",
  marginBottom: 10,
  marginTop: 0,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};
const inputStyle = {
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8,
  padding: "10px 14px",
  color: "#e2e8f0",
  fontSize: "0.95rem",
  boxSizing: "border-box",
  minHeight: 44,
  outline: "none",
};
const addBtnStyle = (disabled) => ({
  padding: "10px 18px",
  minHeight: 44,
  background: disabled ? "rgba(255,255,255,0.04)" : "rgba(99,102,241,0.2)",
  border: "1px solid rgba(99,102,241,0.3)",
  borderRadius: 8,
  color: disabled ? "rgba(255,255,255,0.25)" : "#a5b4fc",
  fontWeight: 600,
  fontSize: "0.9rem",
  cursor: disabled ? "not-allowed" : "pointer",
  flexShrink: 0,
});
const domainChipStyle = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 20,
  padding: "5px 12px",
  color: "rgba(255,255,255,0.7)",
};
const chipRemoveStyle = {
  background: "none",
  border: "none",
  color: "rgba(255,255,255,0.35)",
  cursor: "pointer",
  padding: "0 0 0 2px",
  fontSize: "0.8rem",
  minWidth: 20,
  minHeight: 20,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};
const healthBtnStyle = (disabled) => ({
  width: "100%",
  padding: "12px",
  minHeight: 48,
  background: disabled ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8,
  color: disabled ? "rgba(255,255,255,0.35)" : "rgba(255,255,255,0.75)",
  fontSize: "0.9rem",
  fontWeight: 500,
  cursor: disabled ? "not-allowed" : "pointer",
});
const backBtnStyle = {
  flex: "0 0 auto",
  padding: "16px 20px",
  minHeight: 52,
  background: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 10,
  color: "rgba(255,255,255,0.6)",
  fontSize: "1rem",
  cursor: "pointer",
};
const completeBtnStyle = (disabled) => ({
  flex: 1,
  padding: "16px",
  minHeight: 52,
  background: disabled ? "rgba(99,102,241,0.4)" : "#6366f1",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: "1rem",
  fontWeight: 600,
  cursor: disabled ? "not-allowed" : "pointer",
});
