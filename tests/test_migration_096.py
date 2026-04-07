from pathlib import Path
import re


def _migration_sql() -> str:
    repo_root = Path(__file__).resolve().parent.parent
    return (repo_root / "migrations" / "096_production_hardening.sql").read_text()


def test_client_id_foreign_keys_tolerate_existing_orphan_rows():
    sql = _migration_sql()

    for constraint_name in ("leads_client_id_fkey", "conversations_client_id_fkey"):
        add_constraint = re.search(
            rf"ADD CONSTRAINT {constraint_name}\s+"
            r"FOREIGN KEY \(client_id\) REFERENCES tenants\(id\) ON DELETE CASCADE\s+"
            r"NOT VALID;",
            sql,
            re.MULTILINE,
        )

        assert add_constraint, f"{constraint_name} must be added NOT VALID"
        assert f"VALIDATE CONSTRAINT {constraint_name}" in sql
