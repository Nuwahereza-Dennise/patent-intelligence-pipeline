"""
============================================================
  Global Patent Intelligence Pipeline
  Step 2: Data Cleaning with pandas
============================================================

This script reads the raw PatentsView TSV files, cleans them,
and saves tidy CSV files ready for loading into the database.

Cleaning steps per table:
  patents   → drop nulls in key fields, parse dates, extract year,
              strip whitespace, cap abstract length
  inventors → normalise names, fill missing country as 'Unknown'
  companies → deduplicate names, drop rows with no name
  relations → drop any rows with missing IDs
"""

import os
import pandas as pd
import re

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE      = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR   = os.path.join(BASE, "data", "raw")
CLEAN_DIR = os.path.join(BASE, "data", "clean")
os.makedirs(CLEAN_DIR, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_tsv(filename: str, usecols: list, nrows: int = None) -> pd.DataFrame:
    """Read a PatentsView TSV with sensible defaults."""
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"\n  ✗ '{filename}' not found in data/raw/\n"
            f"    Please run scripts/01_download_data.py first.\n"
        )
    print(f"  Reading {filename} …")
    return pd.read_csv(
        path,
        sep="\t",
        usecols=usecols,
        nrows=nrows,           # None = all rows; set a number to work faster locally
        dtype=str,             # read everything as string first, convert after
        low_memory=False,
        on_bad_lines="skip",
    )


def clean_text(series: pd.Series) -> pd.Series:
    """Strip leading/trailing whitespace and collapse inner spaces."""
    return series.str.strip().str.replace(r"\s+", " ", regex=True)


def title_case_name(series: pd.Series) -> pd.Series:
    """Convert ALL CAPS or all-lower names to Title Case."""
    return series.str.title()


# ── 1. Patents ────────────────────────────────────────────────────────────────

def clean_patents(nrows=None) -> pd.DataFrame:
    print("\n[1/4] Cleaning patents …")

    df = read_tsv(
        "g_patent.tsv",
        usecols=["patent_id", "patent_title", "patent_abstract", "patent_date"],
        nrows=nrows,
    )

    # Rename columns to match our schema
    df.columns = ["patent_id", "title", "abstract", "filing_date"]

    # ── Drop rows missing the key fields
    before = len(df)
    df.dropna(subset=["patent_id", "title", "filing_date"], inplace=True)
    print(f"    Dropped {before - len(df):,} rows with missing ID/title/date")

    # ── Clean text fields
    df["title"]    = clean_text(df["title"])
    df["abstract"] = df["abstract"].fillna("No abstract available.")
    df["abstract"] = clean_text(df["abstract"]).str[:2000]   # cap at 2000 chars

    # ── Parse date and extract year
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    bad_dates = df["filing_date"].isna().sum()
    if bad_dates:
        print(f"    ⚠ {bad_dates:,} unparseable dates — set to NaT")
    df["year"] = df["filing_date"].dt.year.astype("Int64")

    # ── Remove obvious duplicates
    df.drop_duplicates(subset="patent_id", inplace=True)

    # ── Convert date back to ISO string for SQLite
    df["filing_date"] = df["filing_date"].dt.strftime("%Y-%m-%d")

    out_path = os.path.join(CLEAN_DIR, "clean_patents.csv")
    df.to_csv(out_path, index=False)
    print(f"    ✓ {len(df):,} clean patents → {out_path}")
    return df


# ── 2. Inventors ──────────────────────────────────────────────────────────────

def clean_inventors(nrows=None) -> pd.DataFrame:
    print("\n[2/4] Cleaning inventors …")

    df = read_tsv(
        "g_inventor_disambiguated.tsv",
        usecols=["disambig_inventor_id", "disambig_inventor_name_first",
                 "disambig_inventor_name_last", "inventor_country"],
        nrows=nrows,
    )

    df.columns = ["inventor_id", "first_name", "last_name", "country"]

    # ── Build full name
    df["first_name"] = df["first_name"].fillna("").pipe(clean_text).pipe(title_case_name)
    df["last_name"]  = df["last_name"].fillna("").pipe(clean_text).pipe(title_case_name)
    df["name"]       = (df["first_name"] + " " + df["last_name"]).str.strip()

    # Drop rows where we couldn't build any name
    before = len(df)
    df = df[df["name"].str.len() > 0]
    print(f"    Dropped {before - len(df):,} rows with no usable name")

    # ── Standardise country
    df["country"] = df["country"].fillna("Unknown").pipe(clean_text).str.upper()
    df["country"] = df["country"].replace({"": "Unknown", "XX": "Unknown"})

    df = df[["inventor_id", "name", "country"]].drop_duplicates(subset="inventor_id")

    out_path = os.path.join(CLEAN_DIR, "clean_inventors.csv")
    df.to_csv(out_path, index=False)
    print(f"    ✓ {len(df):,} clean inventors → {out_path}")
    return df


# ── 3. Companies (Assignees) ──────────────────────────────────────────────────

def clean_companies(nrows=None) -> pd.DataFrame:
    print("\n[3/4] Cleaning companies …")

    df = read_tsv(
        "g_assignee_disambiguated.tsv",
        usecols=["disambig_assignee_id", "disambig_assignee_organization"],
        nrows=nrows,
    )

    df.columns = ["company_id", "name"]

    # Drop rows with no company name
    before = len(df)
    df.dropna(subset=["name"], inplace=True)
    df = df[df["name"].str.strip().str.len() > 0]
    print(f"    Dropped {before - len(df):,} rows with missing name")

    df["name"] = clean_text(df["name"])

    # Remove clearly personal (non-organisation) entries: single-word names
    # that don't look like company names are kept — PatentsView disambiguates well
    df.drop_duplicates(subset="company_id", inplace=True)

    out_path = os.path.join(CLEAN_DIR, "clean_companies.csv")
    df.to_csv(out_path, index=False)
    print(f"    ✓ {len(df):,} clean companies → {out_path}")
    return df


# ── 4. Relationship Tables ────────────────────────────────────────────────────

def clean_relationships() -> tuple[pd.DataFrame, pd.DataFrame]:
    print("\n[4/4] Cleaning relationship tables …")

    # Patent ↔ Inventor
    inv_rel = read_tsv(
        "g_patent_inventor.tsv",
        usecols=["patent_id", "inventor_id"],
    )
    inv_rel.dropna(inplace=True)
    inv_rel.drop_duplicates(inplace=True)
    inv_path = os.path.join(CLEAN_DIR, "clean_patent_inventor.csv")
    inv_rel.to_csv(inv_path, index=False)
    print(f"    ✓ {len(inv_rel):,} patent–inventor links → {inv_path}")

    # Patent ↔ Company
    co_rel = read_tsv(
        "g_patent_assignee.tsv",
        usecols=["patent_id", "assignee_id"],
    )
    co_rel.columns = ["patent_id", "company_id"]
    co_rel.dropna(inplace=True)
    co_rel.drop_duplicates(inplace=True)
    co_path = os.path.join(CLEAN_DIR, "clean_patent_company.csv")
    co_rel.to_csv(co_path, index=False)
    print(f"    ✓ {len(co_rel):,} patent–company links → {co_path}")

    return inv_rel, co_rel


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(patents, inventors, companies):
    print("\n" + "=" * 60)
    print("  CLEANING SUMMARY")
    print("=" * 60)
    print(f"  Patents   : {len(patents):>10,} records")
    print(f"  Inventors : {len(inventors):>10,} records")
    print(f"  Companies : {len(companies):>10,} records")
    print(f"\n  Year range: {patents['year'].min()} – {patents['year'].max()}")
    print(f"  Countries : {inventors['country'].nunique()} unique")
    print(f"\n  Clean CSVs saved to data/clean/")
    print(f"  Next step: run scripts/03_load_database.py")
    print("=" * 60 + "\n")


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Global Patent Intelligence — Data Cleaner")
    print("=" * 60)

    # Set nrows to e.g. 500_000 for faster local development
    # Set to None to process all data
    SAMPLE_SIZE = None  # change to 500_000 if your machine struggles

    patents   = clean_patents(nrows=SAMPLE_SIZE)
    inventors = clean_inventors(nrows=SAMPLE_SIZE)
    companies = clean_companies(nrows=SAMPLE_SIZE)
    clean_relationships()

    print_summary(patents, inventors, companies)
