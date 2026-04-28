"""
============================================================
  Global Patent Intelligence Pipeline
  Step 3: Load Clean Data into SQLite Database
============================================================

Builds the SQLite database from the clean CSV files.
Creates all tables, applies indexes for fast queries, and
bulk-inserts data using pandas + sqlite3.
"""

import os
import sqlite3
import pandas as pd
import time

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE      = os.path.join(os.path.dirname(__file__), "..")
CLEAN_DIR = os.path.join(BASE, "data", "clean")
DB_PATH   = os.path.join(BASE, "patents.db")

# ── Schema ─────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- ============================================================
--   Global Patent Intelligence — Database Schema
-- ============================================================

PRAGMA journal_mode = WAL;       -- faster concurrent writes
PRAGMA foreign_keys = ON;

-- Core patent records
CREATE TABLE IF NOT EXISTS patents (
    patent_id   TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    abstract    TEXT,
    filing_date TEXT,
    year        INTEGER
);

-- Disambiguated inventor records
CREATE TABLE IF NOT EXISTS inventors (
    inventor_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    country     TEXT DEFAULT 'Unknown'
);

-- Company / assignee records
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL
);

-- Patent ↔ Inventor relationship
CREATE TABLE IF NOT EXISTS patent_inventor (
    patent_id   TEXT,
    inventor_id TEXT,
    PRIMARY KEY (patent_id, inventor_id),
    FOREIGN KEY (patent_id)   REFERENCES patents(patent_id),
    FOREIGN KEY (inventor_id) REFERENCES inventors(inventor_id)
);

-- Patent ↔ Company relationship
CREATE TABLE IF NOT EXISTS patent_company (
    patent_id  TEXT,
    company_id TEXT,
    PRIMARY KEY (patent_id, company_id),
    FOREIGN KEY (patent_id)  REFERENCES patents(patent_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- Indexes for fast analytical queries
CREATE INDEX IF NOT EXISTS idx_patents_year     ON patents(year);
CREATE INDEX IF NOT EXISTS idx_inventors_country ON inventors(country);
CREATE INDEX IF NOT EXISTS idx_pi_patent        ON patent_inventor(patent_id);
CREATE INDEX IF NOT EXISTS idx_pi_inventor      ON patent_inventor(inventor_id);
CREATE INDEX IF NOT EXISTS idx_pc_patent        ON patent_company(patent_id);
CREATE INDEX IF NOT EXISTS idx_pc_company       ON patent_company(company_id);
"""

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_csv(filename: str) -> pd.DataFrame:
    path = os.path.join(CLEAN_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"\n  ✗ '{filename}' not found in data/clean/\n"
            f"    Run scripts/02_clean_data.py first.\n"
        )
    df = pd.read_csv(path, dtype=str, low_memory=False)
    df = df.where(pd.notnull(df), None)   # convert NaN → None for SQLite
    return df


def bulk_insert(conn: sqlite3.Connection, table: str, df: pd.DataFrame,
                chunk_size: int = 50_000) -> None:
    """Insert a DataFrame into a SQLite table in chunks."""
    total = len(df)
    inserted = 0
    for start in range(0, total, chunk_size):
        chunk = df.iloc[start : start + chunk_size]
        chunk.to_sql(table, conn, if_exists="append", index=False)
        inserted += len(chunk)
        pct = inserted / total * 100
        print(f"    [{table}] {inserted:,} / {total:,} rows ({pct:.0f}%)", end="\r")
    print()   # newline after progress


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Global Patent Intelligence — Database Loader")
    print("=" * 60 + "\n")

    # Remove old DB if rebuilding
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("  Old database removed — rebuilding …\n")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.commit()
    print("  ✓ Schema created\n")

    tables = [
        ("patents",          "clean_patents.csv"),
        ("inventors",        "clean_inventors.csv"),
        ("companies",        "clean_companies.csv"),
        ("patent_inventor",  "clean_patent_inventor.csv"),
        ("patent_company",   "clean_patent_company.csv"),
    ]

    for table, csv_file in tables:
        t0 = time.time()
        print(f"  Loading {csv_file} → {table} …")
        df = load_csv(csv_file)
        bulk_insert(conn, table, df)
        conn.commit()
        elapsed = time.time() - t0
        print(f"    ✓ Done in {elapsed:.1f}s")

    # Quick sanity check
    print("\n  Sanity check:")
    for table, _ in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"    {table:<20} {count:>10,} rows")

    conn.close()

    db_size_mb = os.path.getsize(DB_PATH) / 1_000_000
    print(f"\n  Database saved to: patents.db ({db_size_mb:.1f} MB)")
    print(f"  Next step: run scripts/04_run_queries.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
