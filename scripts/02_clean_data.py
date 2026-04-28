"""
============================================================
  Global Patent Intelligence Pipeline
  Step 2: Data Cleaning with pandas
============================================================

Actual files available:
  g_patent.tsv                  -> patent id, title, date
  g_patent_abstract.tsv         -> patent abstracts (separate file)
  g_inventor_disambiguated.tsv  -> inventors + patent_id links
  g_assignee_disambiguated.tsv  -> companies + patent_id links
  g_cpc_current.tsv             -> patent categories (bonus)
"""

import os
import pandas as pd

BASE      = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR   = os.path.join(BASE, "data", "raw")
CLEAN_DIR = os.path.join(BASE, "data", "clean")
os.makedirs(CLEAN_DIR, exist_ok=True)

SAMPLE_SIZE = 500000  # change to 500_000 if your PC is slow

def read_tsv(filename, usecols, nrows=None):
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"\n  X '{filename}' not found in data/raw/\n")
    print(f"  Reading {filename} ...")
    return pd.read_csv(path, sep="\t", usecols=usecols, nrows=nrows,
                       dtype=str, low_memory=False, on_bad_lines="skip")

def clean_text(series):
    return series.str.strip().str.replace(r"\s+", " ", regex=True)

def title_case(series):
    return series.str.title()


# ── 1. Patents ────────────────────────────────────────────────────────────────

def clean_patents():
    print("\n[1/4] Cleaning patents ...")

    patents = read_tsv("g_patent.tsv",
                       usecols=["patent_id", "patent_title", "patent_date"],
                       nrows=SAMPLE_SIZE)
    patents = patents.rename(columns={
        "patent_id":    "patent_id",
        "patent_title": "title",
        "patent_date":  "filing_date"
    })

    abstracts = read_tsv("g_patent_abstract.tsv",
                         usecols=["patent_id", "patent_abstract"],
                         nrows=SAMPLE_SIZE)
    abstracts.columns = ["patent_id", "abstract"]

    print("  Merging patents with abstracts ...")
    df = patents.merge(abstracts, on="patent_id", how="left")

    before = len(df)
    df.dropna(subset=["patent_id", "title", "filing_date"], inplace=True)
    print(f"  Dropped {before - len(df):,} rows with missing fields")

    df["title"]    = clean_text(df["title"])
    df["abstract"] = df["abstract"].fillna("No abstract available.")
    df["abstract"] = clean_text(df["abstract"]).str[:2000]

    # Extract year directly using regex
    df["year"] = df["filing_date"].str.extract(r'(\b(19|20)\d{2}\b)')[0].astype("Int64")
    # Keep only valid patent years
    df = df[df["year"].between(1976, 2025)]

    df.drop_duplicates(subset="patent_id", inplace=True)

    df.to_csv(os.path.join(CLEAN_DIR, "clean_patents.csv"), index=False)
    print(f"  OK {len(df):,} clean patents -> clean_patents.csv")
    return df


# ── 2. Inventors + Links ──────────────────────────────────────────────────────

def clean_inventors():
    print("\n[2/4] Cleaning inventors ...")

    df = read_tsv("g_inventor_disambiguated.tsv",
                  usecols=["patent_id", "inventor_id",
                           "disambig_inventor_name_first",
                           "disambig_inventor_name_last"],
                  nrows=SAMPLE_SIZE)
    df.columns = ["patent_id", "inventor_id", "first_name", "last_name"]

    df["first_name"] = df["first_name"].fillna("").pipe(clean_text).pipe(title_case)
    df["last_name"]  = df["last_name"].fillna("").pipe(clean_text).pipe(title_case)
    df["name"]       = (df["first_name"] + " " + df["last_name"]).str.strip()
    df["country"]    = "Unknown"

    before = len(df)
    df = df[df["name"].str.len() > 0]
    print(f"  Dropped {before - len(df):,} rows with no name")

    inventors = df[["inventor_id", "name", "country"]].drop_duplicates(subset="inventor_id")
    inventors.to_csv(os.path.join(CLEAN_DIR, "clean_inventors.csv"), index=False)
    print(f"  OK {len(inventors):,} unique inventors -> clean_inventors.csv")

    links = df[["patent_id", "inventor_id"]].drop_duplicates().dropna()
    links.to_csv(os.path.join(CLEAN_DIR, "clean_patent_inventor.csv"), index=False)
    print(f"  OK {len(links):,} patent-inventor links -> clean_patent_inventor.csv")

    return inventors, links


# ── 3. Companies + Links ──────────────────────────────────────────────────────

def clean_companies():
    print("\n[3/4] Cleaning companies ...")

    df = read_tsv("g_assignee_disambiguated.tsv",
                  usecols=["patent_id", "assignee_id",
                           "disambig_assignee_organization"],
                  nrows=SAMPLE_SIZE)
    df.columns = ["patent_id", "company_id", "name"]

    before = len(df)
    df.dropna(subset=["name"], inplace=True)
    df = df[df["name"].str.strip().str.len() > 0]
    print(f"  Dropped {before - len(df):,} rows with no organisation name")

    df["name"] = clean_text(df["name"])

    companies = df[["company_id", "name"]].drop_duplicates(subset="company_id")
    companies.to_csv(os.path.join(CLEAN_DIR, "clean_companies.csv"), index=False)
    print(f"  OK {len(companies):,} unique companies -> clean_companies.csv")

    links = df[["patent_id", "company_id"]].drop_duplicates().dropna()
    links.to_csv(os.path.join(CLEAN_DIR, "clean_patent_company.csv"), index=False)
    print(f"  OK {len(links):,} patent-company links -> clean_patent_company.csv")

    return companies, links


# ── 4. CPC Classifications (bonus) ───────────────────────────────────────────

def clean_cpc():
    print("\n[4/4] Cleaning CPC classifications (bonus) ...")

    df = read_tsv("g_cpc_current.tsv",
                  usecols=["patent_id", "cpc_section", "cpc_class", "cpc_subclass"],
                  nrows=SAMPLE_SIZE)

    df.dropna(subset=["patent_id", "cpc_section"], inplace=True)
    df.drop_duplicates(inplace=True)

    section_map = {
        "A": "Human Necessities",
        "B": "Performing Operations & Transporting",
        "C": "Chemistry & Metallurgy",
        "D": "Textiles & Paper",
        "E": "Fixed Constructions",
        "F": "Mechanical Engineering",
        "G": "Physics & Computing",
        "H": "Electricity & Electronics",
        "Y": "Emerging Cross-Sectional Technologies",
    }
    df["technology_area"] = df["cpc_section"].map(section_map).fillna("Other")

    df.to_csv(os.path.join(CLEAN_DIR, "clean_cpc.csv"), index=False)
    print(f"  OK {len(df):,} CPC records -> clean_cpc.csv")
    return df


# ── Summary ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Global Patent Intelligence - Data Cleaner")
    print("=" * 60)

    patents              = clean_patents()
    inventors, inv_links = clean_inventors()
    companies, co_links  = clean_companies()
    clean_cpc()

    print("\n" + "=" * 60)
    print("  CLEANING COMPLETE")
    print("=" * 60)
    print(f"  Patents   : {len(patents):>10,}")
    print(f"  Inventors : {len(inventors):>10,}")
    print(f"  Companies : {len(companies):>10,}")
    print(f"  Year range: {patents['year'].min()} - {patents['year'].max()}")
    print(f"\n  Next step: python scripts/03_load_database.py")
    print("=" * 60 + "\n")