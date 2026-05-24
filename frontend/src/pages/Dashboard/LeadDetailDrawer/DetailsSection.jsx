import { STAGE_OPTIONS } from "./constants";

export default function DetailsSection({
  form,
  onChange,
  assignedTo,
  onAssign,
  teamMembers,
}) {
  return (
    <div className="intel-section">
      <div className="intel-title">Details</div>
      <div className="drawer-field">
        <label className="drawer-label">Stage</label>
        <select
          className="drawer-select"
          value={form.status}
          onChange={onChange("status")}
        >
          {STAGE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Assigned To</label>
        <select
          className="drawer-select"
          value={assignedTo}
          onChange={(e) => onAssign(e.target.value)}
        >
          <option value="">Unassigned</option>
          {teamMembers.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name || m.email}
            </option>
          ))}
        </select>
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Areas of Interest</label>
        <input
          className="drawer-input"
          value={form.areas_of_interest}
          onChange={onChange("areas_of_interest")}
          placeholder="Areas of interest"
        />
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Timeline</label>
        <input
          className="drawer-input"
          value={form.timeline}
          onChange={onChange("timeline")}
          placeholder="Timeline"
        />
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Budget</label>
        <input
          className="drawer-input"
          value={form.budget}
          onChange={onChange("budget")}
          placeholder="Budget"
        />
      </div>
      <div className="drawer-field">
        <label className="drawer-label">Notes</label>
        <textarea
          className="drawer-textarea"
          value={form.conversation_summary}
          onChange={onChange("conversation_summary")}
          placeholder="Add notes..."
          rows={3}
        />
      </div>
    </div>
  );
}
