export function ConversationTagsCard({
  tagDefs,
  newTagName,
  setNewTagName,
  newTagColor,
  setNewTagColor,
  savingTag,
  handleAddTag,
  handleToggleTag,
  handleDeleteTag,
}) {
  return (
    <div className="settings-card">
      <h3>Conversation Tags</h3>
      <p className="settings-card-desc">
        Define tags for AI auto-categorization of conversations. System tags are
        built-in; add custom tags for your business needs.
      </p>

      {tagDefs.length === 0 ? (
        <p style={emptyTextStyle}>
          No tags defined yet. Add custom tags below, or the AI will use default
          categories when auto-tagging conversations.
        </p>
      ) : (
        <div style={listStyle}>
          {tagDefs.map((tag) => (
            <TagRow
              key={tag.id}
              tag={tag}
              handleToggleTag={handleToggleTag}
              handleDeleteTag={handleDeleteTag}
            />
          ))}
        </div>
      )}

      <div style={formPanelStyle}>
        <label style={formLabelStyle}>Add custom tag</label>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="color"
            value={newTagColor}
            onChange={(e) => setNewTagColor(e.target.value)}
            style={{
              width: 32,
              height: 32,
              padding: 0,
              border: "1px solid var(--border)",
              borderRadius: 6,
              cursor: "pointer",
              background: "transparent",
            }}
            title="Tag color"
          />
          <input
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            placeholder="e.g. pricing-inquiry"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAddTag();
            }}
            style={{ flex: 1 }}
          />
          <button
            className="btn-primary"
            onClick={handleAddTag}
            disabled={savingTag || !newTagName.trim()}
            style={{ whiteSpace: "nowrap" }}
          >
            {savingTag ? "Adding..." : "Add Tag"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TagRow({ tag, handleToggleTag, handleDeleteTag }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 12px",
        borderRadius: 8,
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        opacity: tag.is_enabled ? 1 : 0.5,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: tag.tag_color || "#6b7280",
            flexShrink: 0,
          }}
        />
        <span style={{ fontSize: "0.9rem", color: "var(--text-primary)" }}>
          {tag.tag_name}
        </span>
        <span
          style={{
            fontSize: "0.7rem",
            padding: "2px 6px",
            borderRadius: 4,
            background: tag.is_system
              ? "rgba(59,130,246,0.15)"
              : "rgba(139,92,246,0.15)",
            color: tag.is_system
              ? "rgba(96,165,250,1)"
              : "rgba(167,139,250,1)",
          }}
        >
          {tag.is_system ? "system" : "custom"}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button
          onClick={() => handleToggleTag(tag)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "0.8rem",
            color: tag.is_enabled ? "rgba(34,197,94,0.9)" : "var(--text-muted)",
          }}
          title={tag.is_enabled ? "Disable tag" : "Enable tag"}
        >
          {tag.is_enabled ? "enabled" : "disabled"}
        </button>
        {!tag.is_system && (
          <button
            onClick={() => handleDeleteTag(tag.id)}
            style={smallTextButtonStyle}
            title="Delete custom tag"
          >
            delete
          </button>
        )}
      </div>
    </div>
  );
}

export function CustomFieldsCard({
  cfLoadError,
  customFieldDefs,
  newFieldName,
  setNewFieldName,
  newFieldType,
  setNewFieldType,
  newFieldOptions,
  setNewFieldOptions,
  newFieldRequired,
  setNewFieldRequired,
  savingField,
  deletingFieldId,
  handleAddCustomField,
  handleDeleteCustomField,
}) {
  return (
    <div className="settings-card">
      <h3>Custom Fields</h3>
      <p className="settings-card-desc">
        Add custom fields to collect additional information on each lead. Fields
        appear in the lead detail panel and can be filled in for any contact.
      </p>

      {cfLoadError && (
        <p style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 8 }}>
          {cfLoadError}
        </p>
      )}

      {customFieldDefs.length === 0 && !cfLoadError ? (
        <p style={emptyTextStyle}>
          No custom fields yet. Add fields below to track additional information
          on your leads, such as "Preferred contact time", "Project type", or
          "Lead source".
        </p>
      ) : (
        <div style={listStyle}>
          {customFieldDefs.map((field) => (
            <CustomFieldRow
              key={field.id}
              field={field}
              deletingFieldId={deletingFieldId}
              handleDeleteCustomField={handleDeleteCustomField}
            />
          ))}
        </div>
      )}

      <div style={{ ...formPanelStyle, padding: "14px 16px" }}>
        <label style={{ ...formLabelStyle, marginBottom: 10 }}>
          Add a new field
        </label>
        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            alignItems: "flex-start",
          }}
        >
          <input
            value={newFieldName}
            onChange={(e) => setNewFieldName(e.target.value)}
            placeholder="Field name (e.g. Project Type)"
            style={{ flex: "2 1 160px", minWidth: 140 }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAddCustomField();
            }}
          />
          <select
            value={newFieldType}
            onChange={(e) => {
              setNewFieldType(e.target.value);
              setNewFieldOptions("");
            }}
            style={fieldTypeSelectStyle}
          >
            <option value="text">Text</option>
            <option value="number">Number</option>
            <option value="dropdown">Dropdown</option>
            <option value="date">Date</option>
            <option value="checkbox">Checkbox</option>
          </select>
          {newFieldType === "dropdown" && (
            <input
              value={newFieldOptions}
              onChange={(e) => setNewFieldOptions(e.target.value)}
              placeholder="Options: Yes, No, Maybe"
              style={{ flex: "3 1 180px", minWidth: 150 }}
              title="Enter comma-separated options"
            />
          )}
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              cursor: "pointer",
              color: "var(--text-secondary)",
              fontSize: "0.85rem",
              whiteSpace: "nowrap",
              alignSelf: "center",
            }}
          >
            <input
              type="checkbox"
              checked={newFieldRequired}
              onChange={(e) => setNewFieldRequired(e.target.checked)}
              style={{ width: "auto" }}
            />
            Required
          </label>
          <button
            className="btn-primary"
            onClick={handleAddCustomField}
            disabled={savingField || !newFieldName.trim()}
            style={{ whiteSpace: "nowrap", alignSelf: "flex-start" }}
          >
            {savingField ? "Adding..." : "Add Field"}
          </button>
        </div>
        {newFieldType === "dropdown" && (
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "8px 0 0" }}>
            Enter comma-separated options for the dropdown (e.g. "Option A,
            Option B, Option C")
          </p>
        )}
      </div>
    </div>
  );
}

function CustomFieldRow({
  field,
  deletingFieldId,
  handleDeleteCustomField,
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "9px 14px",
        borderRadius: 8,
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span
          style={{
            fontSize: "0.9rem",
            color: "var(--text-primary)",
            fontWeight: 500,
          }}
        >
          {field.name}
        </span>
        <span style={fieldTypeBadgeStyle}>{field.field_type}</span>
        {field.is_required && <span style={requiredBadgeStyle}>Required</span>}
        {field.field_type === "dropdown" &&
          field.options &&
          field.options.length > 0 && (
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              ({field.options.join(", ")})
            </span>
          )}
      </div>
      <button
        onClick={() => handleDeleteCustomField(field.id)}
        disabled={deletingFieldId === field.id}
        style={{ ...smallTextButtonStyle, padding: "2px 4px" }}
        title="Delete field"
      >
        {deletingFieldId === field.id ? "..." : "delete"}
      </button>
    </div>
  );
}

const emptyTextStyle = {
  color: "var(--text-muted)",
  fontSize: "0.85rem",
  marginTop: 8,
};

const listStyle = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  marginTop: 8,
};

const formPanelStyle = {
  marginTop: 16,
  padding: "12px 14px",
  borderRadius: 8,
  background: "var(--bg-secondary)",
  border: "1px solid var(--border)",
};

const formLabelStyle = {
  fontSize: "0.8rem",
  color: "var(--text-muted)",
  display: "block",
  marginBottom: 8,
};

const smallTextButtonStyle = {
  background: "none",
  border: "none",
  cursor: "pointer",
  color: "var(--text-muted)",
  fontSize: "0.8rem",
};

const fieldTypeSelectStyle = {
  flex: "1 1 110px",
  padding: "8px 10px",
  borderRadius: 6,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.9rem",
};

const fieldTypeBadgeStyle = {
  fontSize: "0.7rem",
  padding: "2px 8px",
  borderRadius: 4,
  background: "rgba(0,191,255,0.12)",
  color: "var(--accent, #00bfff)",
  fontWeight: 600,
  textTransform: "uppercase",
};

const requiredBadgeStyle = {
  fontSize: "0.7rem",
  padding: "2px 8px",
  borderRadius: 4,
  background: "rgba(239,68,68,0.12)",
  color: "#f87171",
  fontWeight: 600,
};
