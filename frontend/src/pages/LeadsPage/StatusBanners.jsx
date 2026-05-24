export default function StatusBanners({
  error,
  importResult,
  onDismissImport,
}) {
  return (
    <>
      {error && (
        <div className="error-banner" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      {importResult && (
        <div
          style={{
            marginBottom: "1rem",
            padding: "0.75rem 1rem",
            background: "var(--bg-card)",
            borderRadius: 8,
            border: "1px solid var(--border)",
            fontSize: "0.9rem",
          }}
        >
          Imported: {importResult.created} created, {importResult.updated}{" "}
          updated
          {importResult.total_errors > 0 &&
            `, ${importResult.total_errors} error${importResult.total_errors !== 1 ? "s" : ""}`}
          <button
            onClick={onDismissImport}
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
            }}
          >
            dismiss
          </button>
        </div>
      )}
    </>
  );
}
