"""
AgentNexLiFy internal MCP server — FastMCP template.

Extend with project-specific tools that no public MCP covers.
Wire into .mcp.json once tools are added.

Run standalone for smoke test:
    uv run python server.py
"""

from fastmcp import FastMCP

mcp = FastMCP("agentnexlify-internal")


@mcp.tool()
def widget_diff() -> dict:
    """Check widget/ vs frontend/public/widget/ byte-identical invariant.

    Returns:
        {"identical": bool, "diff_summary": str | None}
    """
    import hashlib
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    src = repo_root / "widget" / "agentnexlify-widget.js"
    dst = repo_root / "frontend" / "public" / "widget" / "agentnexlify-widget.js"

    if not src.exists() or not dst.exists():
        return {"identical": False, "diff_summary": f"missing: src={src.exists()} dst={dst.exists()}"}

    src_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    dst_hash = hashlib.sha256(dst.read_bytes()).hexdigest()
    return {
        "identical": src_hash == dst_hash,
        "diff_summary": None if src_hash == dst_hash else f"{src_hash[:12]} != {dst_hash[:12]}",
    }


@mcp.tool()
def migration_next() -> dict:
    """Return next available migration number in migrations/.

    Returns:
        {"next_number": int, "last_file": str}
    """
    import pathlib
    import re

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "migrations"

    if not migrations_dir.exists():
        return {"next_number": 1, "last_file": ""}

    pattern = re.compile(r"^(\d{3})_")
    nums = []
    last_file = ""
    for f in sorted(migrations_dir.glob("*.sql")):
        m = pattern.match(f.name)
        if m:
            nums.append(int(m.group(1)))
            last_file = f.name

    next_num = max(nums) + 1 if nums else 1
    return {"next_number": next_num, "last_file": last_file}


@mcp.resource("agentnexlify://stack-info")
def stack_info() -> str:
    """Static reference: project tech stack."""
    return (
        "Backend: FastAPI / Python 3.11 / Pydantic / Supabase\n"
        "Frontend: React 18 / Vite 6 / Tailwind\n"
        "DB: Supabase Postgres with RLS\n"
        "AI: Claude (opus-4-7, sonnet-4-6, haiku-4-5-20251001)\n"
        "Hosting: Railway (backend), Vercel (frontend)\n"
        "Critical invariants: client_id (not tenant_id), status (not lead_stage), "
        "areas_of_interest (not service_interest), widget byte-identical"
    )


if __name__ == "__main__":
    mcp.run()
