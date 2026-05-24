import { STAGES } from "../Dashboard/LeadPipeline";

export default function Toolbar({
  search,
  onSearchChange,
  stageFilter,
  onStageFilterChange,
  assignedFilter,
  onAssignedFilterChange,
  teamMembers,
  view,
  onViewChange,
  importing,
  onImportClick,
  fileInputRef,
  onImportFile,
  onFindDuplicates,
  onExportCSV,
}) {
  return (
    <div className="leads-toolbar">
      <input
        className="leads-search"
        type="text"
        placeholder="Search leads..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <select
        className="leads-filter"
        value={stageFilter}
        onChange={(e) => onStageFilterChange(e.target.value)}
      >
        <option value="">All Stages</option>
        {STAGES.map((s) => (
          <option key={s.key} value={s.key}>
            {s.label}
          </option>
        ))}
      </select>
      <select
        className="leads-filter"
        value={assignedFilter}
        onChange={(e) => onAssignedFilterChange(e.target.value)}
      >
        <option value="">All Assignees</option>
        {teamMembers.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name || m.email}
          </option>
        ))}
      </select>
      <div className="leads-view-toggle">
        <button
          className={`view-btn${view === "board" ? " active" : ""}`}
          onClick={() => onViewChange("board")}
        >
          Board
        </button>
        <button
          className={`view-btn${view === "table" ? " active" : ""}`}
          onClick={() => onViewChange("table")}
        >
          Table
        </button>
      </div>
      <button
        className="leads-export-btn"
        onClick={onImportClick}
        disabled={importing}
      >
        {importing ? "Importing..." : "Import CSV"}
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        style={{ display: "none" }}
        onChange={onImportFile}
      />
      <button className="leads-export-btn" onClick={onFindDuplicates}>
        Find Duplicates
      </button>
      <button className="leads-export-btn" onClick={onExportCSV}>
        Export CSV
      </button>
    </div>
  );
}
