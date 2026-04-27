"""
============================================================
  Global Patent Intelligence Pipeline
  Step 5: Report Generator
============================================================

Produces three output formats:
  A. Console Report  — formatted terminal summary
  B. CSV Exports     — top_inventors.csv, top_companies.csv,
                       country_trends.csv, yearly_trends.csv
  C. JSON Report     — summary.json
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime

BASE        = os.path.join(os.path.dirname(__file__), "..")
DB_PATH     = os.path.join(BASE, "patents.db")
REPORTS_DIR = os.path.join(BASE, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


# ── Queries ───────────────────────────────────────────────────────────────────

Q1 = """
SELECT i.name AS inventor_name, i.country,
       COUNT(DISTINCT pi.patent_id) AS patent_count
FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
GROUP BY i.inventor_id ORDER BY patent_count DESC LIMIT 20;
"""

Q2 = """
SELECT c.name AS company_name,
       COUNT(DISTINCT pc.patent_id) AS patent_count
FROM companies c JOIN patent_company pc ON c.company_id = pc.company_id
GROUP BY c.company_id ORDER BY patent_count DESC LIMIT 20;
"""

Q3 = """
SELECT i.country,
       COUNT(DISTINCT pi.patent_id) AS patent_count,
       COUNT(DISTINCT i.inventor_id) AS inventor_count,
       ROUND(100.0 * COUNT(DISTINCT pi.patent_id)
             / (SELECT COUNT(*) FROM patent_inventor), 2) AS pct_of_total
FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
WHERE i.country != 'Unknown'
GROUP BY i.country ORDER BY patent_count DESC LIMIT 30;
"""

Q4 = """
SELECT year, COUNT(*) AS total_patents
FROM patents WHERE year IS NOT NULL AND year BETWEEN 1976 AND 2025
GROUP BY year ORDER BY year;
"""

Q7 = """
WITH counts AS (
    SELECT i.inventor_id, i.name AS inventor_name, i.country,
           COUNT(DISTINCT pi.patent_id) AS patent_count
    FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
    WHERE i.country != 'Unknown'
    GROUP BY i.inventor_id
)
SELECT inventor_name, country, patent_count,
       RANK() OVER (PARTITION BY country ORDER BY patent_count DESC) AS country_rank,
       DENSE_RANK() OVER (ORDER BY patent_count DESC) AS global_rank
FROM counts ORDER BY patent_count DESC LIMIT 100;
"""


def get_conn():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "\n  patents.db not found. Run scripts/03_load_database.py first.\n"
        )
    return sqlite3.connect(DB_PATH)


def run_queries(conn):
    print("  Running queries …")
    results = {}
    for name, sql in [("Q1", Q1), ("Q2", Q2), ("Q3", Q3), ("Q4", Q4), ("Q7", Q7)]:
        results[name] = pd.read_sql_query(sql, conn)
        print(f"    {name} → {len(results[name]):,} rows")
    return results


# ── A. Console Report ─────────────────────────────────────────────────────────

def print_console_report(results, total_patents, total_inventors):
    w = 60
    print(f"\n{'='*w}")
    print(f"{'GLOBAL PATENT INTELLIGENCE REPORT':^{w}}")
    print(f"{'Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M'):^{w}}")
    print(f"{'='*w}\n")
    print(f"  {'Total Patents Analysed:':<35} {total_patents:>10,}")
    print(f"  {'Total Unique Inventors:':<35} {total_inventors:>10,}\n")

    print(f"  ── TOP 10 INVENTORS {'─'*(w-22)}")
    for rank, row in enumerate(results["Q1"].head(10).itertuples(), 1):
        print(f"  {rank:>2}. {row.inventor_name:<30} {row.patent_count:>6,}  [{row.country}]")

    print(f"\n  ── TOP 10 COMPANIES {'─'*(w-22)}")
    for rank, row in enumerate(results["Q2"].head(10).itertuples(), 1):
        print(f"  {rank:>2}. {row.company_name:<35} {row.patent_count:>6,}")

    print(f"\n  ── TOP 15 COUNTRIES {'─'*(w-22)}")
    for rank, row in enumerate(results["Q3"].head(15).itertuples(), 1):
        print(f"  {rank:>2}. {row.country:<10}  {row.patent_count:>8,}  ({row.pct_of_total:.1f}%)")

    trend = results["Q4"].tail(10)
    peak  = trend["total_patents"].max()
    print(f"\n  ── PATENT FILINGS: LAST 10 YEARS {'─'*(w-35)}")
    for row in trend.itertuples():
        bar = "█" * int(row.total_patents / peak * 30)
        print(f"  {int(row.year)}  {bar:<30}  {row.total_patents:>8,}")

    print(f"\n{'='*w}")
    print(f"{'END OF REPORT':^{w}}")
    print(f"{'='*w}\n")


# ── B. CSV Exports ────────────────────────────────────────────────────────────

def export_csvs(results):
    mapping = {
        "top_inventors.csv":    results["Q1"],
        "top_companies.csv":    results["Q2"],
        "country_trends.csv":   results["Q3"],
        "yearly_trends.csv":    results["Q4"],
        "country_rankings.csv": results["Q7"],
    }
    for fname, df in mapping.items():
        path = os.path.join(REPORTS_DIR, fname)
        df.to_csv(path, index=False)
        print(f"  ✓ {fname}  ({len(df):,} rows)")


# ── C. JSON Report ────────────────────────────────────────────────────────────

def export_json(results, total_patents, total_inventors):
    tr  = results["Q4"]
    r5  = tr[tr["year"] >= tr["year"].max() - 4]["total_patents"].sum()
    p5  = tr[(tr["year"] >= tr["year"].max()-9) &
             (tr["year"] <  tr["year"].max()-4)]["total_patents"].sum()
    growth = round((r5 - p5) / p5 * 100, 1) if p5 else None

    report = {
        "metadata": {
            "title":     "Global Patent Intelligence Report",
            "generated": datetime.now().isoformat(),
            "source":    "USPTO PatentsView",
        },
        "summary": {
            "total_patents":     total_patents,
            "total_inventors":   total_inventors,
            "5yr_growth_rate_%": growth,
        },
        "top_inventors": [
            {"rank": r, "name": row.inventor_name,
             "country": row.country, "patents": row.patent_count}
            for r, row in enumerate(results["Q1"].head(10).itertuples(), 1)
        ],
        "top_companies": [
            {"rank": r, "name": row.company_name, "patents": row.patent_count}
            for r, row in enumerate(results["Q2"].head(10).itertuples(), 1)
        ],
        "top_countries": [
            {"country": row.country, "patents": row.patent_count,
             "share_%": row.pct_of_total}
            for row in results["Q3"].itertuples()
        ],
        "yearly_trends": [
            {"year": int(row.year), "total_patents": row.total_patents}
            for row in tr.itertuples()
        ],
    }

    path = os.path.join(REPORTS_DIR, "summary.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  ✓ summary.json")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Global Patent Intelligence — Report Generator")
    print("=" * 60 + "\n")

    conn            = get_conn()
    results         = run_queries(conn)
    total_patents   = conn.execute("SELECT COUNT(*) FROM patents").fetchone()[0]
    total_inventors = conn.execute("SELECT COUNT(*) FROM inventors").fetchone()[0]
    conn.close()

    print_console_report(results, total_patents, total_inventors)

    print("  Exporting CSVs …")
    export_csvs(results)

    print("\n  Exporting JSON …")
    export_json(results, total_patents, total_inventors)

    print(f"\n  All reports saved to reports/")
    print(f"  Next step: python scripts/06_visualize.py  (bonus marks!)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
