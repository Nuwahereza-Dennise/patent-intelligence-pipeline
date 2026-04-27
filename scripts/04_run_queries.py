"""
============================================================
  Global Patent Intelligence Pipeline
  Step 4: SQL Analytical Queries
============================================================

Runs all 7 required SQL queries against the patents database
and returns results as pandas DataFrames.

Q1 → Top Inventors   (aggregation)
Q2 → Top Companies   (aggregation)
Q3 → Top Countries   (aggregation)
Q4 → Trends Over Time (GROUP BY year)
Q5 → JOIN query      (patents + inventors + companies)
Q6 → CTE query       (WITH … AS …)
Q7 → Ranking query   (window function RANK())
"""

import os
import sqlite3
import pandas as pd

BASE    = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE, "patents.db")


def get_connection() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "\n  ✗ patents.db not found.\n"
            "    Run scripts/03_load_database.py first.\n"
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Q1: Top Inventors — Who has the most patents?
# ─────────────────────────────────────────────────────────────────────────────

Q1_TOP_INVENTORS = """
SELECT
    i.name                         AS inventor_name,
    i.country,
    COUNT(DISTINCT pi.patent_id)   AS patent_count
FROM inventors i
JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
GROUP BY i.inventor_id, i.name, i.country
ORDER BY patent_count DESC
LIMIT 20;
"""

# ─────────────────────────────────────────────────────────────────────────────
# Q2: Top Companies — Which companies own the most patents?
# ─────────────────────────────────────────────────────────────────────────────

Q2_TOP_COMPANIES = """
SELECT
    c.name                         AS company_name,
    COUNT(DISTINCT pc.patent_id)   AS patent_count
FROM companies c
JOIN patent_company pc ON c.company_id = pc.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC
LIMIT 20;
"""

# ─────────────────────────────────────────────────────────────────────────────
# Q3: Countries — Which countries produce the most patents?
# ─────────────────────────────────────────────────────────────────────────────

Q3_COUNTRIES = """
SELECT
    i.country,
    COUNT(DISTINCT pi.patent_id)   AS patent_count,
    COUNT(DISTINCT i.inventor_id)  AS inventor_count,
    ROUND(
        100.0 * COUNT(DISTINCT pi.patent_id)
              / (SELECT COUNT(*) FROM patent_inventor),
        2
    )                              AS pct_of_total
FROM inventors i
JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
WHERE i.country != 'Unknown'
GROUP BY i.country
ORDER BY patent_count DESC
LIMIT 30;
"""

# ─────────────────────────────────────────────────────────────────────────────
# Q4: Trends Over Time — How many patents per year?
# ─────────────────────────────────────────────────────────────────────────────

Q4_TRENDS = """
SELECT
    p.year,
    COUNT(*)                        AS total_patents,
    COUNT(DISTINCT pi.inventor_id)  AS unique_inventors,
    COUNT(DISTINCT pc.company_id)   AS unique_companies
FROM patents p
LEFT JOIN patent_inventor pi ON p.patent_id = pi.patent_id
LEFT JOIN patent_company  pc ON p.patent_id = pc.patent_id
WHERE p.year IS NOT NULL
  AND p.year BETWEEN 1976 AND 2025
GROUP BY p.year
ORDER BY p.year ASC;
"""

# ─────────────────────────────────────────────────────────────────────────────
# Q5: JOIN Query — Combine patents, inventors, and companies
# ─────────────────────────────────────────────────────────────────────────────

Q5_JOIN = """
SELECT
    p.patent_id,
    p.title,
    p.year,
    i.name          AS inventor_name,
    i.country       AS inventor_country,
    c.name          AS company_name
FROM patents p
JOIN patent_inventor pi ON p.patent_id = pi.patent_id
JOIN inventors i        ON pi.inventor_id = i.inventor_id
LEFT JOIN patent_company pc ON p.patent_id = pc.patent_id
LEFT JOIN companies c       ON pc.company_id = c.company_id
WHERE p.year >= 2015
ORDER BY p.year DESC, p.patent_id
LIMIT 200;
"""

# ─────────────────────────────────────────────────────────────────────────────
# Q6: CTE Query — High-output inventors at top-3 companies
# ─────────────────────────────────────────────────────────────────────────────

Q6_CTE = """
-- Step 1: find the top 3 companies by patent volume
WITH top_companies AS (
    SELECT
        c.company_id,
        c.name                        AS company_name,
        COUNT(DISTINCT pc.patent_id)  AS company_patents
    FROM companies c
    JOIN patent_company pc ON c.company_id = pc.company_id
    GROUP BY c.company_id, c.name
    ORDER BY company_patents DESC
    LIMIT 3
),
-- Step 2: find inventors who have filed patents at those companies
inventor_at_top_cos AS (
    SELECT
        i.inventor_id,
        i.name                        AS inventor_name,
        i.country,
        tc.company_name,
        COUNT(DISTINCT pi.patent_id)  AS patents_here
    FROM inventors i
    JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
    JOIN patent_company  pc ON pi.patent_id  = pc.patent_id
    JOIN top_companies   tc ON pc.company_id = tc.company_id
    GROUP BY i.inventor_id, i.name, i.country, tc.company_name
)
-- Step 3: return the most prolific inventors at each top company
SELECT *
FROM inventor_at_top_cos
ORDER BY company_name, patents_here DESC
LIMIT 60;
"""

# ─────────────────────────────────────────────────────────────────────────────
# Q7: Ranking Query — Rank inventors per country using window functions
# ─────────────────────────────────────────────────────────────────────────────

Q7_RANKING = """
WITH inventor_counts AS (
    SELECT
        i.inventor_id,
        i.name          AS inventor_name,
        i.country,
        COUNT(DISTINCT pi.patent_id) AS patent_count
    FROM inventors i
    JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
    WHERE i.country != 'Unknown'
    GROUP BY i.inventor_id, i.name, i.country
),
ranked AS (
    SELECT
        inventor_name,
        country,
        patent_count,
        RANK()       OVER (PARTITION BY country ORDER BY patent_count DESC) AS country_rank,
        DENSE_RANK() OVER (ORDER BY patent_count DESC)                       AS global_rank,
        ROUND(
            100.0 * patent_count
                  / SUM(patent_count) OVER (PARTITION BY country),
            1
        )                                                                    AS pct_of_country
    FROM inventor_counts
)
SELECT *
FROM ranked
WHERE country_rank <= 5        -- top 5 per country
ORDER BY patent_count DESC
LIMIT 100;
"""


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

ALL_QUERIES = {
    "Q1_top_inventors":   Q1_TOP_INVENTORS,
    "Q2_top_companies":   Q2_TOP_COMPANIES,
    "Q3_countries":       Q3_COUNTRIES,
    "Q4_trends":          Q4_TRENDS,
    "Q5_join":            Q5_JOIN,
    "Q6_cte":             Q6_CTE,
    "Q7_ranking":         Q7_RANKING,
}


def run_all(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    """Execute all queries and return a dict of DataFrames."""
    results = {}
    for name, sql in ALL_QUERIES.items():
        print(f"  Running {name} …", end=" ")
        df = pd.read_sql_query(sql, conn)
        results[name] = df
        print(f"→ {len(df):,} rows")
    return results


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Global Patent Intelligence — SQL Queries")
    print("=" * 60 + "\n")

    conn = get_connection()
    results = run_all(conn)
    conn.close()

    print("\n  Preview of Q1 (Top Inventors):")
    print(results["Q1_top_inventors"].head(5).to_string(index=False))

    print("\n  Preview of Q2 (Top Companies):")
    print(results["Q2_top_companies"].head(5).to_string(index=False))

    print("\n  ✓ All queries complete.")
    print("    Next step: run scripts/05_generate_reports.py")
    print("=" * 60 + "\n")
