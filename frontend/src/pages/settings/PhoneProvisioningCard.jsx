export default function PhoneProvisioningCard({
  provisionedPhone,
  phoneAreaCode,
  setPhoneAreaCode,
  availableNumbers,
  searchingNumbers,
  provisioningPhone,
  releasingPhone,
  phoneError,
  phoneSuccess,
  setAvailableNumbers,
  setPhoneError,
  handleSearchNumbers,
  handleProvision,
  handleReleasePhone,
}) {
  return (
    <div className="settings-card">
      <h3>Business Phone Number</h3>
      <p className="settings-card-desc">
        Provision a dedicated business phone number to enable the AI Answering
        Service, Missed Call Text-Back, and Two-Way SMS with your leads.
      </p>

      {phoneError && <PhoneAlert tone="error">{phoneError}</PhoneAlert>}
      {phoneSuccess && <PhoneAlert tone="success">{phoneSuccess}</PhoneAlert>}

      {provisionedPhone ? (
        <ProvisionedNumber
          provisionedPhone={provisionedPhone}
          releasingPhone={releasingPhone}
          handleReleasePhone={handleReleasePhone}
        />
      ) : (
        <PhoneSearch
          phoneAreaCode={phoneAreaCode}
          setPhoneAreaCode={setPhoneAreaCode}
          availableNumbers={availableNumbers}
          searchingNumbers={searchingNumbers}
          provisioningPhone={provisioningPhone}
          setAvailableNumbers={setAvailableNumbers}
          setPhoneError={setPhoneError}
          handleSearchNumbers={handleSearchNumbers}
          handleProvision={handleProvision}
        />
      )}
    </div>
  );
}

function PhoneAlert({ tone, children }) {
  const isError = tone === "error";

  return (
    <div
      style={{
        marginBottom: 12,
        padding: "8px 12px",
        borderRadius: 6,
        fontSize: "0.85rem",
        background: isError ? "rgba(239,68,68,0.08)" : "rgba(34,197,94,0.08)",
        border: isError
          ? "1px solid rgba(239,68,68,0.2)"
          : "1px solid rgba(34,197,94,0.2)",
        color: isError ? "var(--red, #ef4444)" : "var(--green, #4ade80)",
      }}
    >
      {children}
    </div>
  );
}

function ProvisionedNumber({
  provisionedPhone,
  releasingPhone,
  handleReleasePhone,
}) {
  return (
    <div>
      <div
        style={{
          padding: "12px 14px",
          borderRadius: 8,
          background: "rgba(34,197,94,0.08)",
          border: "1px solid rgba(34,197,94,0.2)",
          marginBottom: 12,
        }}
      >
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginBottom: 4,
          }}
        >
          Active phone number
        </div>
        <div
          style={{
            fontSize: "1.2rem",
            fontWeight: 700,
            color: "var(--green, #4ade80)",
            letterSpacing: 1,
          }}
        >
          {provisionedPhone}
        </div>
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginTop: 4,
          }}
        >
          Calls and SMS are routed through this number to your AI assistant.
        </div>
      </div>
      <button
        className="btn-danger"
        onClick={handleReleasePhone}
        disabled={releasingPhone}
        style={{ fontSize: "0.85rem" }}
      >
        {releasingPhone ? "Releasing..." : "Release Number"}
      </button>
    </div>
  );
}

function PhoneSearch({
  phoneAreaCode,
  setPhoneAreaCode,
  availableNumbers,
  searchingNumbers,
  provisioningPhone,
  setAvailableNumbers,
  setPhoneError,
  handleSearchNumbers,
  handleProvision,
}) {
  return (
    <div>
      <div className="settings-field">
        <label>Area Code</label>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={phoneAreaCode}
            onChange={(e) => {
              setPhoneAreaCode(e.target.value.replace(/\D/g, "").slice(0, 3));
              setAvailableNumbers([]);
              setPhoneError(null);
            }}
            placeholder="e.g. 512"
            maxLength={3}
            style={{ width: 100, flex: "none" }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearchNumbers();
            }}
          />
          <button
            className="btn-secondary"
            onClick={handleSearchNumbers}
            disabled={searchingNumbers || !phoneAreaCode.trim()}
          >
            {searchingNumbers ? "Searching..." : "Search Available"}
          </button>
        </div>
        <span className="settings-field-hint">
          Enter your preferred area code to find local numbers.
        </span>
      </div>

      {availableNumbers.length > 0 && (
        <AvailableNumbers
          availableNumbers={availableNumbers}
          provisioningPhone={provisioningPhone}
          handleProvision={handleProvision}
        />
      )}

      {!availableNumbers.length && !searchingNumbers && (
        <div
          style={{
            marginTop: 10,
            padding: "10px 14px",
            borderRadius: 8,
            fontSize: "0.83rem",
            background: "rgba(59,130,246,0.07)",
            border: "1px solid rgba(59,130,246,0.2)",
            color: "var(--text-secondary)",
          }}
        >
          A provisioned number enables: AI Answering Service, Missed Call
          Text-Back, and Two-Way SMS. Search above to get started.
        </div>
      )}
    </div>
  );
}

function AvailableNumbers({
  availableNumbers,
  provisioningPhone,
  handleProvision,
}) {
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 8 }}>
        {availableNumbers.length} number{availableNumbers.length !== 1 ? "s" : ""}{" "}
        available
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          marginBottom: 12,
        }}
      >
        {availableNumbers.map((number) => (
          <AvailableNumberRow key={number.phone_number} number={number} />
        ))}
      </div>
      <button
        className="btn-primary"
        onClick={handleProvision}
        disabled={provisioningPhone}
      >
        {provisioningPhone
          ? "Provisioning..."
          : "Provision First Available Number"}
      </button>
      <span className="settings-field-hint" style={{ display: "block", marginTop: 6 }}>
        This will purchase the first available number and configure it for your
        account.
      </span>
    </div>
  );
}

function AvailableNumberRow({ number }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "8px 12px",
        borderRadius: 8,
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
      }}
    >
      <div>
        <span
          style={{
            fontWeight: 600,
            color: "var(--text-primary)",
            marginRight: 8,
          }}
        >
          {number.friendly_name}
        </span>
        {number.locality && (
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            {number.locality}
            {number.region ? `, ${number.region}` : ""}
          </span>
        )}
      </div>
      <div style={{ display: "flex", gap: 6, fontSize: "0.72rem" }}>
        {number.capabilities?.voice && (
          <CapabilityBadge color="#60a5fa" background="rgba(59,130,246,0.15)">
            Voice
          </CapabilityBadge>
        )}
        {number.capabilities?.sms && (
          <CapabilityBadge color="#4ade80" background="rgba(34,197,94,0.15)">
            SMS
          </CapabilityBadge>
        )}
      </div>
    </div>
  );
}

function CapabilityBadge({ color, background, children }) {
  return (
    <span
      style={{
        padding: "2px 6px",
        borderRadius: 4,
        background,
        color,
      }}
    >
      {children}
    </span>
  );
}
