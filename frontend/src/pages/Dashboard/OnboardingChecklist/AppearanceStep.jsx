import { COLOR_SWATCHES } from "./constants";

export default function AppearanceStep({
  selectedColor,
  setSelectedColor,
  customColor,
  setCustomColor,
  position,
  setPosition,
  saving,
  saveError,
  onSave,
}) {
  const previewColor = customColor.match(/^#[0-9a-fA-F]{6}$/)
    ? customColor
    : selectedColor;

  return (
    <div className="onboarding-step-body">
      <label className="onboarding-field-label">Brand Color</label>
      <div className="color-swatches">
        {COLOR_SWATCHES.map((c) => (
          <button
            key={c}
            className={`color-swatch${selectedColor === c ? " active" : ""}`}
            style={{ background: c }}
            onClick={() => {
              setSelectedColor(c);
              setCustomColor("");
            }}
          />
        ))}
        <input
          className="onboarding-color-input"
          type="text"
          placeholder="#hex"
          value={customColor}
          onChange={(e) => setCustomColor(e.target.value)}
          maxLength={7}
        />
      </div>

      <label className="onboarding-field-label">Widget Position</label>
      <div className="onboarding-radio-group">
        <label className="onboarding-radio">
          <input
            type="radio"
            name="position"
            value="bottom-right"
            checked={position === "bottom-right"}
            onChange={() => setPosition("bottom-right")}
          />
          Bottom Right
        </label>
        <label className="onboarding-radio">
          <input
            type="radio"
            name="position"
            value="bottom-left"
            checked={position === "bottom-left"}
            onChange={() => setPosition("bottom-left")}
          />
          Bottom Left
        </label>
      </div>

      <div className="onboarding-mini-preview">
        <div className="mini-preview-window">
          <div
            className={`mini-preview-bubble ${position}`}
            style={{ background: previewColor }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
              <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
            </svg>
          </div>
        </div>
      </div>

      <button
        className="onboarding-save-btn"
        onClick={onSave}
        disabled={saving}
      >
        {saving ? "Saving..." : "Save Appearance"}
      </button>
      {saveError && <div className="onboarding-error">{saveError}</div>}
    </div>
  );
}
