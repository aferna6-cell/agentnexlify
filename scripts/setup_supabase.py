#!/usr/bin/env python3
"""Initialize Supabase database tables for AgentNexLiFy.

Usage:
    python -m scripts.setup_supabase

Reads tables.sql and executes it against your Supabase instance via the REST API.
Note: For initial setup, run the SQL directly in the Supabase SQL Editor
since the REST API doesn't support raw DDL. This script verifies connectivity.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.models.database import get_supabase  # noqa: E402


def main():
    sql_path = Path(__file__).parent.parent / "backend" / "models" / "tables.sql"
    sql = sql_path.read_text()

    print("AgentNexLiFy — Database Setup")
    print("=" * 50)
    print()
    print("Step 1: Testing Supabase connection...")

    try:
        db = get_supabase()
        # Try a simple query to verify connectivity
        db.table("clients").select("id").limit(1).execute()
        print("  Connected to Supabase successfully!")
        print()
        print("Step 2: If tables already exist, you're all set.")
        print("  If this is a fresh setup, run the following SQL")
        print("  in your Supabase SQL Editor (supabase.com > SQL Editor):")
        print()
        print("-" * 50)
        print(sql)
        print("-" * 50)
    except Exception as e:
        err_str = str(e)
        if "relation" in err_str and "does not exist" in err_str:
            print("  Connected, but tables don't exist yet.")
            print()
            print("  Run the following SQL in your Supabase SQL Editor:")
            print()
            print("-" * 50)
            print(sql)
            print("-" * 50)
        else:
            print(f"  Connection failed: {e}")
            print()
            print("  Check your .env file has correct SUPABASE_URL and SUPABASE_SERVICE_KEY")
            sys.exit(1)


if __name__ == "__main__":
    main()
