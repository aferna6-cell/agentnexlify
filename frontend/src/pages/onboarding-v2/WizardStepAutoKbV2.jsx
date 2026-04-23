import { useState, useRef } from "react";
import { autoKb, saveStep } from "../../utils/api/onboardingV2";

const SCAN_TIMEOUT_MS = 30000;

function CollapseSection({ title, count, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div
      style={{
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 8,
        marginBottom: 8,
        overflow: "hidden",
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
          background: "rgba(255,255,255,0.04)",
          border: "none",
          color: "#e2e8f0",
          fontSize: "0.9rem",
          fontWeight: 600,
          cursor: "pointer",
          minHeight: 48,
          textAlign: "left",
        }}
      >
        <span>
          {title}
          {count != null && (
            <span
              style={{
                marginLeft: 8,
                background: "rgba(99,102,241,0.2)",
                color: "#a5b4fc",
                fontSize: "0.75rem",
                padding: "2px 8px",
                borderRadius: 99,
                fontWeight: 500,
              }}
            >
              {count}
            </span>
          )}
        </span>
        <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.8rem" }}>
          {open ? "Hide" : "Show"}
        </span>
      </button>
      {open && (
        <div
          style={{
            padding: "12px 16px",
            background: "rgba(255,255,255,0.02)",
            borderTop: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export default function WizardStepAutoKbV2({
  wizardData,
  token,
  onNext,
  onBack,
}) {
  const websiteUrl = wizardData.websiteUrl || "";
  const domainDisplay = websiteUrl
    .replace(/^https?:\/\//, "")
    .replace(/\/$/, "");

  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(wizardData.autoKbResult || null);
  const [scanError, setScanError] = useState(null);
  const [saving, setSaving] = useState(false);
  const abortRef = useRef(null);

  async function handleScan() {
    if (scanning) return;
    setScanError(null);
    setScanResult(null);
    setScanning(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const timeoutId = setTimeout(() => controller.abort(), SCAN_TIMEOUT_MS);

    try {
      const result = await autoKb(token, websiteUrl, controller.signal);
      setScanResult(result);
    } catch (err) {
      if (err.name === "AbortError" || err.message?.includes("abort")) {
        setScanError(
          "Scan timed out — couldn't reach your site in 30 seconds. You can add info manually in the next step.",
        );
      } else {
        setScanError(
          "Couldn't reach your site — you can add info manually in the next step.",
        );
      }
    } finally {
      clearTimeout(timeoutId);
      setScanning(false);
    }
  }

  async function handleNext(skip = false) {
    if (saving) return;
    setSaving(true);
    try {
      await saveStep(token, 3, { auto_kb_result: skip ? null : scanResult });
      onNext({ autoKbResult: skip ? null : scanResult });
    } catch (err) {
      setScanError(err.message || "Failed to save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  const services = scanResult?.services || [];
  const faqs = scanResult?.faqs || [];
  const hours = scanResult?.hours || null;

  return (
    <div>
      <h2 style={headingStyle}>Auto-fill from your website</h2>
      <p style={subStyle}>
        We scan your site and extract services, FAQs, and hours to pre-fill your
        AI assistant.
      </p>

      {/* Website URL display */}
      <div style={urlBannerStyle}>
        <span style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.8rem" }}>
          Scanning
        </span>
        <span
          style={{
            fontWeight: 600,
            fontSize: "0.95rem",
            wordBreak: "break-all",
          }}
        >
          {domainDisplay || "your website"}
        </span>
      </div>

      {/* Scan CTA */}
      {!scanResult && !scanning && (
        <button
          type="button"
          onClick={handleScan}
          disabled={!websiteUrl}
          style={scanBtnStyle(!websiteUrl)}
        >
          Scan {domainDisplay || "website"}
        </button>
      )}

      {/* Loading */}
      {scanning && (
        <div style={loadingWrapStyle}>
          <div style={spinnerStyle} />
          <span style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.95rem" }}>
            Scanning your website...
          </span>
          <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.8rem" }}>
            Up to 30 seconds
          </span>
        </div>
      )}

      {/* Error state */}
      {scanError && (
        <div style={errorStyle}>
          {scanError}
          <button
            type="button"
            onClick={handleScan}
            style={{
              marginTop: 10,
              display: "block",
              background: "none",
              border: "1px solid rgba(252,165,165,0.3)",
              borderRadius: 6,
              color: "#fca5a5",
              padding: "6px 14px",
              fontSize: "0.85rem",
              cursor: "pointer",
              minHeight: 36,
            }}
          >
            Try again
          </button>
        </div>
      )}

      {/* Scan results */}
      {scanResult && !scanning && (
        <div style={{ marginTop: 16, marginBottom: 8 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 14,
              color: "#4ade80",
              fontSize: "0.9rem",
              fontWeight: 600,
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="7" stroke="#4ade80" strokeWidth="1.5" />
              <polyline
                points="5,8 7,10 11,6"
                stroke="#4ade80"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Scan complete
          </div>

          {services.length > 0 && (
            <CollapseSection
              title="Services found"
              count={services.length}
              defaultOpen
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {services.map((s, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: "0.85rem",
                      color: "rgba(255,255,255,0.7)",
                    }}
                  >
                    {s}
                  </div>
                ))}
              </div>
            </CollapseSection>
          )}

          {faqs.length > 0 && (
            <CollapseSection title="FAQs found" count={faqs.length}>
              <div
                style={{ display: "flex", flexDirection: "column", gap: 10 }}
              >
                {faqs.map((f, i) => (
                  <div key={i}>
                    <div
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        color: "rgba(255,255,255,0.8)",
                        marginBottom: 2,
                      }}
                    >
                      {f.q}
                    </div>
                    <div
                      style={{
                        fontSize: "0.82rem",
                        color: "rgba(255,255,255,0.5)",
                      }}
                    >
                      {f.a}
                    </div>
                  </div>
                ))}
              </div>
            </CollapseSection>
          )}

          {hours && (
            <CollapseSection title="Hours found" count={null}>
              <div
                style={{
                  fontSize: "0.85rem",
                  color: "rgba(255,255,255,0.7)",
                  whiteSpace: "pre-wrap",
                }}
              >
                {typeof hours === "string"
                  ? hours
                  : JSON.stringify(hours, null, 2)}
              </div>
            </CollapseSection>
          )}

          {services.length === 0 && faqs.length === 0 && !hours && (
            <div style={emptyResultStyle}>
              Couldn't extract structured data from your site. You can add it
              manually in the next step.
            </div>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginTop: 28 }}>
        <button type="button" onClick={onBack} style={backBtnStyle}>
          Back
        </button>

        {/* Skip always visible */}
        {!scanResult && !scanning && (
          <button
            type="button"
            onClick={() => handleNext(true)}
            disabled={saving}
            style={skipBtnStyle(saving)}
          >
            {saving ? "Saving..." : "Skip this step"}
          </button>
        )}

        {scanResult && !scanning && (
          <button
            type="button"
            onClick={() => handleNext(false)}
            disabled={saving}
            style={nextBtnStyle(saving)}
          >
            {saving ? "Saving..." : "Use this data"}
          </button>
        )}
      </div>

      {!scanResult && !scanning && (
        <div style={{ textAlign: "center", marginTop: 8 }}>
          <button
            type="button"
            onClick={() => handleNext(true)}
            disabled={saving}
            style={{
              background: "none",
              border: "none",
              color: "rgba(255,255,255,0.35)",
              fontSize: "0.82rem",
              cursor: "pointer",
              padding: "4px 0",
              minHeight: 32,
            }}
          >
            Skip and add manually
          </button>
        </div>
      )}
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
const urlBannerStyle = {
  display: "flex",
  flexDirection: "column",
  gap: 4,
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 8,
  padding: "12px 16px",
  marginBottom: 20,
};
const scanBtnStyle = (disabled) => ({
  width: "100%",
  padding: "16px",
  minHeight: 52,
  background: disabled ? "rgba(99,102,241,0.3)" : "#6366f1",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: "1rem",
  fontWeight: 600,
  cursor: disabled ? "not-allowed" : "pointer",
  marginBottom: 8,
});
const loadingWrapStyle = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: 12,
  padding: "32px 0",
};
const spinnerStyle = {
  width: 32,
  height: 32,
  border: "3px solid rgba(99,102,241,0.2)",
  borderTop: "3px solid #6366f1",
  borderRadius: "50%",
  animation: "spin 0.8s linear infinite",
};
const errorStyle = {
  background: "rgba(220,38,38,0.12)",
  border: "1px solid rgba(220,38,38,0.25)",
  color: "#fca5a5",
  padding: "12px 16px",
  borderRadius: 8,
  fontSize: "0.9rem",
  marginBottom: 8,
};
const emptyResultStyle = {
  background: "rgba(255,255,255,0.03)",
  border: "1px dashed rgba(255,255,255,0.1)",
  borderRadius: 8,
  padding: "16px",
  fontSize: "0.85rem",
  color: "rgba(255,255,255,0.4)",
  textAlign: "center",
};
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
const skipBtnStyle = (disabled) => ({
  flex: 1,
  padding: "16px",
  minHeight: 52,
  background: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 10,
  color: disabled ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.7)",
  fontSize: "1rem",
  fontWeight: 500,
  cursor: disabled ? "not-allowed" : "pointer",
});
const nextBtnStyle = (disabled) => ({
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
