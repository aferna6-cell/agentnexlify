export default function InsuranceSection({ form, lead, onChange }) {
  const show =
    form.insurance_carrier ||
    form.insurance_member_id ||
    form.insurance_group ||
    lead.insurance_carrier;

  if (!show) return null;

  return (
    <div className="intel-section">
      <div className="intel-title">Insurance</div>
      <div className="drawer-field">
        <label className="drawer-label">Carrier</label>
        <input
          className="drawer-input"
          value={form.insurance_carrier}
          onChange={onChange("insurance_carrier")}
          placeholder="e.g. Delta Dental, Cigna"
        />
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Member ID</label>
        <input
          className="drawer-input"
          value={form.insurance_member_id}
          onChange={onChange("insurance_member_id")}
          placeholder="Member/Policy ID"
        />
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Group Number</label>
        <input
          className="drawer-input"
          value={form.insurance_group}
          onChange={onChange("insurance_group")}
          placeholder="Group #"
        />
      </div>
    </div>
  );
}
