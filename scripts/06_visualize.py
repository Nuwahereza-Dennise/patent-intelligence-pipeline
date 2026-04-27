"""
============================================================
  Global Patent Intelligence Pipeline
  Step 6: Visualizations (Bonus Marks)
============================================================

Generates 5 publication-quality charts using matplotlib/seaborn
and saves them to visualizations/

Charts produced:
  1. Top 15 Companies — horizontal bar chart
  2. Top 15 Countries — bar chart with % labels
  3. Patent Filings Over Time — line chart with trend
  4. Top 10 Inventors — dot plot
  5. Country Share — treemap-style breakdown
"""

import os
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — safe for scripts
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

BASE   = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE, "patents.db")
VIZ_DIR = os.path.join(BASE, "visualizations")
os.makedirs(VIZ_DIR, exist_ok=True)

# ── Style ─────────────────────────────────────────────────────────────────────

PALETTE   = "#1a1a2e"   # dark navy background
ACCENT    = "#e94560"   # vivid red accent
ACCENT2   = "#0f3460"   # deep blue
LIGHT     = "#f5f5f5"   # near-white text
MID       = "#a8a8b3"   # muted text

def set_style() -> None:
    plt.rcParams.update({
        "figure.facecolor":  PALETTE,
        "axes.facecolor":    "#16213e",
        "axes.edgecolor":    MID,
        "axes.labelcolor":   LIGHT,
        "axes.titlecolor":   LIGHT,
        "axes.titlesize":    14,
        "axes.labelsize":    11,
        "xtick.color":       MID,
        "ytick.color":       MID,
        "text.color":        LIGHT,
        "grid.color":        "#2a2a4a",
        "grid.linestyle":    "--",
        "grid.linewidth":    0.5,
        "font.family":       "DejaVu Sans",
    })

def watermark(ax) -> None:
    ax.text(0.99, 0.01, "Source: USPTO PatentsView",
            transform=ax.transAxes, fontsize=7,
            color=MID, ha="right", va="bottom")


# ── Helper ────────────────────────────────────────────────────────────────────

def query(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query(sql, conn)
    conn.close()
    return df


def save(fig, name: str) -> None:
    path = os.path.join(VIZ_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=PALETTE)
    plt.close(fig)
    print(f"  ✓ Saved {name}")


# ── Chart 1: Top Companies ────────────────────────────────────────────────────

def chart_top_companies() -> None:
    df = query("""
        SELECT c.name AS company, COUNT(DISTINCT pc.patent_id) AS patents
        FROM companies c
        JOIN patent_company pc ON c.company_id = pc.company_id
        GROUP BY c.company_id ORDER BY patents DESC LIMIT 15
    """)
    df = df.sort_values("patents")   # ascending so largest is at top

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(df["company"], df["patents"],
                   color=[ACCENT if i == len(df)-1 else ACCENT2
                          for i in range(len(df))],
                   edgecolor="none", height=0.65)

    for bar, val in zip(bars, df["patents"]):
        ax.text(bar.get_width() + df["patents"].max() * 0.005,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=9, color=LIGHT)

    ax.set_xlabel("Number of Patents")
    ax.set_title("Top 15 Patent-Holding Companies", pad=15, fontweight="bold")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)
    watermark(ax)
    fig.tight_layout()
    save(fig, "01_top_companies.png")


# ── Chart 2: Top Countries ────────────────────────────────────────────────────

def chart_top_countries() -> None:
    df = query("""
        SELECT i.country, COUNT(DISTINCT pi.patent_id) AS patents
        FROM inventors i
        JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
        WHERE i.country != 'Unknown'
        GROUP BY i.country ORDER BY patents DESC LIMIT 15
    """)

    colors = [ACCENT if i == 0 else ACCENT2 for i in range(len(df))]
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(df["country"], df["patents"], color=colors, edgecolor="none", width=0.7)

    for bar, val in zip(bars, df["patents"]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + df["patents"].max() * 0.01,
                f"{val:,}", ha="center", fontsize=8, color=LIGHT)

    ax.set_ylabel("Patent Count")
    ax.set_title("Top 15 Patent-Producing Countries", pad=15, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    plt.xticks(rotation=30, ha="right")
    watermark(ax)
    fig.tight_layout()
    save(fig, "02_top_countries.png")


# ── Chart 3: Patent Filings Over Time ─────────────────────────────────────────

def chart_yearly_trend() -> None:
    df = query("""
        SELECT year, COUNT(*) AS patents
        FROM patents
        WHERE year BETWEEN 1976 AND 2025
          AND year IS NOT NULL
        GROUP BY year ORDER BY year
    """)
    df["year"] = df["year"].astype(int)

    fig, ax = plt.subplots(figsize=(13, 5))

    ax.fill_between(df["year"], df["patents"], alpha=0.2, color=ACCENT)
    ax.plot(df["year"], df["patents"], color=ACCENT, linewidth=2.5, zorder=3)

    # Highlight peak year
    peak = df.loc[df["patents"].idxmax()]
    ax.annotate(
        f"Peak: {int(peak['year'])}\n{int(peak['patents']):,} patents",
        xy=(peak["year"], peak["patents"]),
        xytext=(peak["year"] - 8, peak["patents"] * 0.95),
        arrowprops=dict(arrowstyle="->", color=LIGHT, lw=1.2),
        fontsize=9, color=LIGHT,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=ACCENT2, alpha=0.8),
    )

    ax.set_xlabel("Year")
    ax.set_ylabel("Patents Granted")
    ax.set_title("Global Patent Filings Over Time (1976 – 2025)", pad=15, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(alpha=0.3)
    ax.set_axisbelow(True)
    watermark(ax)
    fig.tight_layout()
    save(fig, "03_yearly_trend.png")


# ── Chart 4: Top Inventors (Dot Plot) ────────────────────────────────────────

def chart_top_inventors() -> None:
    df = query("""
        SELECT i.name AS inventor, i.country,
               COUNT(DISTINCT pi.patent_id) AS patents
        FROM inventors i
        JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
        GROUP BY i.inventor_id ORDER BY patents DESC LIMIT 10
    """)
    df = df.sort_values("patents")

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hlines(df["inventor"], 0, df["patents"], color=MID, linewidth=1.2, linestyle="--")
    sc = ax.scatter(df["patents"], df["inventor"], s=120,
                    color=ACCENT, zorder=5, edgecolors="white", linewidths=0.8)

    for _, row in df.iterrows():
        ax.text(row["patents"] + df["patents"].max() * 0.01,
                row["inventor"],
                f"{row['patents']:,}  [{row['country']}]",
                va="center", fontsize=9, color=LIGHT)

    ax.set_xlabel("Total Patents")
    ax.set_title("Top 10 Most Prolific Inventors", pad=15, fontweight="bold")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)
    watermark(ax)
    fig.tight_layout()
    save(fig, "04_top_inventors.png")


# ── Chart 5: Country Share (Treemap-style pie) ────────────────────────────────

def chart_country_share() -> None:
    df = query("""
        SELECT i.country, COUNT(DISTINCT pi.patent_id) AS patents
        FROM inventors i
        JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
        WHERE i.country != 'Unknown'
        GROUP BY i.country ORDER BY patents DESC LIMIT 8
    """)

    total_other = query("""
        SELECT SUM(cnt) FROM (
            SELECT COUNT(DISTINCT pi.patent_id) AS cnt
            FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
            WHERE i.country != 'Unknown'
            GROUP BY i.country ORDER BY cnt DESC LIMIT -1 OFFSET 8
        )
    """).iloc[0, 0] or 0

    if total_other > 0:
        other_row = pd.DataFrame([{"country": "Other", "patents": int(total_other)}])
        df = pd.concat([df, other_row], ignore_index=True)

    cmap   = plt.get_cmap("RdBu")
    colors = [cmap(i / len(df)) for i in range(len(df))]

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        df["patents"], labels=df["country"], autopct="%1.1f%%",
        colors=colors, pctdistance=0.82, startangle=140,
        wedgeprops=dict(edgecolor=PALETTE, linewidth=2),
    )
    for t in texts + autotexts:
        t.set_color(LIGHT)
        t.set_fontsize(10)

    ax.set_title("Global Patent Share by Country", pad=20, fontweight="bold")
    watermark(ax)
    fig.tight_layout()
    save(fig, "05_country_share.png")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Global Patent Intelligence — Visualizations")
    print("=" * 60 + "\n")

    if not os.path.exists(DB_PATH):
        print("  ✗ patents.db not found. Run 03_load_database.py first.")
        return

    set_style()

    chart_top_companies()
    chart_top_countries()
    chart_yearly_trend()
    chart_top_inventors()
    chart_country_share()

    print(f"\n  All charts saved to visualizations/")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
