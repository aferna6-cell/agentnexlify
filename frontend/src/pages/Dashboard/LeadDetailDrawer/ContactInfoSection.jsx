export default function ContactInfoSection({ form, onChange }) {
  return (
    <div className="intel-section">
      <div className="intel-title">Contact Info</div>
      <div className="drawer-field">
        <label className="drawer-label">Name</label>
        <input
          className="drawer-input"
          value={form.name}
          onChange={onChange("name")}
          placeholder="Lead name"
        />
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Email</label>
        <input
          className="drawer-input"
          type="email"
          value={form.email}
          onChange={onChange("email")}
          placeholder="email@example.com"
        />
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Phone</label>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input
            className="drawer-input"
            type="tel"
            value={form.phone}
            onChange={onChange("phone")}
            placeholder="(555) 123-4567"
            style={{ flex: 1 }}
          />
          {form.phone && (
            <a
              href={`tel:${form.phone}`}
              title="Call"
              style={{
                color: "var(--accent)",
                fontSize: "1.1rem",
                textDecoration: "none",
                flexShrink: 0,
              }}
            >
              &#9742;
            </a>
          )}
        </div>
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Date of Birth</label>
        <input
          className="drawer-input"
          type="date"
          value={form.date_of_birth}
          onChange={onChange("date_of_birth")}
        />
      </div>
    </div>
  );
}
