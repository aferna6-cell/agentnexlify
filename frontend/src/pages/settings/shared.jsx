export function SaveButton({
  saving,
  saved,
  onSave,
  label = "Save Changes",
  style,
}) {
  return (
    <button
      className="btn-primary"
      onClick={onSave}
      disabled={saving}
      style={style}
    >
      {saving ? "Saving..." : saved ? "Saved!" : label}
    </button>
  );
}

export function CheckboxSettingRow({
  id,
  checked,
  disabled,
  onChange,
  label,
}) {
  return (
    <div
      className="settings-field"
      style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        id={id}
        style={{ width: "auto" }}
        disabled={disabled}
      />
      <label htmlFor={id} style={{ margin: 0, cursor: "pointer" }}>
        {label}
      </label>
    </div>
  );
}
