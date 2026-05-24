export default function Pagination({
  page,
  totalPages,
  totalLeads,
  onPageChange,
}) {
  if (totalPages <= 1) return null;
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: 12,
        padding: "16px 0",
        marginTop: 8,
      }}
    >
      <button
        disabled={page <= 1}
        onClick={() => onPageChange(Math.max(1, page - 1))}
        className="btn btn-secondary"
        style={{ padding: "6px 14px", fontSize: 13 }}
      >
        Previous
      </button>
      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
        Page {page} of {totalPages} ({totalLeads} leads)
      </span>
      <button
        disabled={page >= totalPages}
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        className="btn btn-secondary"
        style={{ padding: "6px 14px", fontSize: 13 }}
      >
        Next
      </button>
    </div>
  );
}
