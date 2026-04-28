"""
============================================================
  Global Patent Intelligence Pipeline
  dashboard.py — Streamlit Interactive Dashboard
============================================================

Run with:
    streamlit run dashboard.py

Opens automatically at http://localhost:8501
"""

import os
import json
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Global Patent Intelligence",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE        = os.path.dirname(__file__)
DB_PATH     = os.path.join(BASE, "patents.db")
REPORTS_DIR = os.path.join(BASE, "reports")
VIZ_DIR     = os.path.join(BASE, "visualizations")

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .metric-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border-left: 4px solid #38bdf8;
    }
    .metric-value { font-size: 32px; font-weight: 700; color: #38bdf8; }
    .metric-label { font-size: 13px; color: #94a3b8; margin-top: 4px; }
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: #f1f5f9;
        padding: 8px 0;
        border-bottom: 2px solid #334155;
        margin-bottom: 16px;
    }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Database Connection ───────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data
def run_query(sql):
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    return pd.read_sql_query(sql, conn)

# ── Load Summary JSON ─────────────────────────────────────────────────────────

@st.cache_data
def load_summary():
    path = os.path.join(REPORTS_DIR, "summary.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/USPTO_seal.svg/200px-USPTO_seal.svg.png", width=80)
    st.markdown("## 🔬 Patent Intelligence")
    st.markdown("*Powered by USPTO PatentsView*")
    st.divider()

    page = st.radio(
        "Navigate",
        ["📊 Overview", "🏆 Top Inventors", "🏢 Top Companies",
         "📈 Trends", "🔍 Search Patents", "🗄️ Run SQL"],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown("**Data Summary**")

    conn = get_connection()
    if conn:
        total_patents   = conn.execute("SELECT COUNT(*) FROM patents").fetchone()[0]
        total_inventors = conn.execute("SELECT COUNT(*) FROM inventors").fetchone()[0]
        total_companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        st.metric("Patents",   f"{total_patents:,}")
        st.metric("Inventors", f"{total_inventors:,}")
        st.metric("Companies", f"{total_companies:,}")
    else:
        st.error("Database not found. Run the pipeline first.")

# ── PAGE: Overview ────────────────────────────────────────────────────────────

if page == "📊 Overview":
    st.title("🔬 Global Patent Intelligence Dashboard")
    st.markdown("*Real-world patent data from USPTO PatentsView — analysed with Python & SQL*")
    st.divider()

    if not os.path.exists(DB_PATH):
        st.error("⚠️ Database not found. Please run `python scripts/03_load_database.py` first.")
        st.stop()

    # ── Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{total_patents:,}</div>
            <div class="metric-label">Total Patents</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card" style="border-color:#a78bfa">
            <div class="metric-value" style="color:#a78bfa">{total_inventors:,}</div>
            <div class="metric-label">Unique Inventors</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card" style="border-color:#34d399">
            <div class="metric-value" style="color:#34d399">{total_companies:,}</div>
            <div class="metric-label">Companies</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        year_range = conn.execute(
            "SELECT MIN(year), MAX(year) FROM patents WHERE year IS NOT NULL"
        ).fetchone()
        yr_text = f"{year_range[0]}–{year_range[1]}" if year_range[0] else "N/A"
        st.markdown(f"""<div class="metric-card" style="border-color:#fb923c">
            <div class="metric-value" style="color:#fb923c; font-size:24px">{yr_text}</div>
            <div class="metric-label">Year Range</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Charts side by side
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-header">🏢 Top 10 Companies</div>', unsafe_allow_html=True)
        co_df = run_query("""
            SELECT c.name AS company, COUNT(DISTINCT pc.patent_id) AS patents
            FROM companies c JOIN patent_company pc ON c.company_id = pc.company_id
            GROUP BY c.company_id ORDER BY patents DESC LIMIT 10
        """)
        if not co_df.empty:
            # Shorten long names
            co_df["company"] = co_df["company"].str[:35]
            co_df = co_df.sort_values("patents")
            fig, ax = plt.subplots(figsize=(7, 5))
            fig.patch.set_facecolor("#1e293b")
            ax.set_facecolor("#1e293b")
            ax.barh(co_df["company"], co_df["patents"], color="#38bdf8", edgecolor="none")
            ax.set_xlabel("Patents", color="#94a3b8")
            ax.tick_params(colors="#94a3b8", labelsize=8)
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
            for spine in ax.spines.values():
                spine.set_edgecolor("#334155")
            ax.grid(axis="x", color="#334155", alpha=0.5)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close()

    with col_b:
        st.markdown('<div class="section-header">🏆 Top 10 Inventors</div>', unsafe_allow_html=True)
        inv_df = run_query("""
            SELECT i.name AS inventor, COUNT(DISTINCT pi.patent_id) AS patents
            FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
            GROUP BY i.inventor_id ORDER BY patents DESC LIMIT 10
        """)
        if not inv_df.empty:
            inv_df = inv_df.sort_values("patents")
            fig, ax = plt.subplots(figsize=(7, 5))
            fig.patch.set_facecolor("#1e293b")
            ax.set_facecolor("#1e293b")
            ax.barh(inv_df["inventor"], inv_df["patents"], color="#a78bfa", edgecolor="none")
            ax.set_xlabel("Patents", color="#94a3b8")
            ax.tick_params(colors="#94a3b8", labelsize=8)
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
            for spine in ax.spines.values():
                spine.set_edgecolor("#334155")
            ax.grid(axis="x", color="#334155", alpha=0.5)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close()

    # ── Yearly trend
    st.divider()
    st.markdown('<div class="section-header">📈 Patent Filings Over Time</div>', unsafe_allow_html=True)
    trend_df = run_query("""
        SELECT year, COUNT(*) AS patents FROM patents
        WHERE year IS NOT NULL GROUP BY year ORDER BY year
    """)
    if not trend_df.empty:
        st.bar_chart(trend_df.set_index("year")["patents"])


# ── PAGE: Top Inventors ───────────────────────────────────────────────────────

elif page == "🏆 Top Inventors":
    st.title("🏆 Top Inventors")
    st.markdown("Ranked by total number of granted patents")
    st.divider()

    limit = st.slider("Show top N inventors", 5, 50, 20)

    df = run_query(f"""
        SELECT i.name AS inventor_name, i.country,
               COUNT(DISTINCT pi.patent_id) AS patent_count
        FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
        GROUP BY i.inventor_id ORDER BY patent_count DESC LIMIT {limit}
    """)

    if not df.empty:
        df.index = df.index + 1
        df.index.name = "Rank"
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.markdown("**Visual breakdown**")
        fig, ax = plt.subplots(figsize=(10, max(4, limit // 3)))
        fig.patch.set_facecolor("#1e293b")
        ax.set_facecolor("#1e293b")
        sorted_df = df.sort_values("patent_count")
        bars = ax.barh(sorted_df["inventor_name"], sorted_df["patent_count"],
                       color="#a78bfa", edgecolor="none")
        ax.set_xlabel("Total Patents", color="#94a3b8")
        ax.tick_params(colors="#94a3b8", labelsize=9)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
        for spine in ax.spines.values():
            spine.set_edgecolor("#334155")
        ax.grid(axis="x", color="#334155", alpha=0.5)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close()

        st.divider()
        csv = df.to_csv()
        st.download_button("⬇️ Download as CSV", csv,
                           "top_inventors.csv", "text/csv")


# ── PAGE: Top Companies ───────────────────────────────────────────────────────

elif page == "🏢 Top Companies":
    st.title("🏢 Top Patent-Holding Companies")
    st.divider()

    limit = st.slider("Show top N companies", 5, 50, 20)

    df = run_query(f"""
        SELECT c.name AS company_name,
               COUNT(DISTINCT pc.patent_id) AS patent_count,
               COUNT(DISTINCT pi.inventor_id) AS unique_inventors
        FROM companies c
        JOIN patent_company pc  ON c.company_id  = pc.company_id
        JOIN patent_inventor pi ON pc.patent_id  = pi.patent_id
        GROUP BY c.company_id ORDER BY patent_count DESC LIMIT {limit}
    """)

    if not df.empty:
        df.index = df.index + 1
        df.index.name = "Rank"
        st.dataframe(df, use_container_width=True)

        st.divider()
        fig, ax = plt.subplots(figsize=(10, max(4, limit // 3)))
        fig.patch.set_facecolor("#1e293b")
        ax.set_facecolor("#1e293b")
        sorted_df = df.sort_values("patent_count")
        sorted_df["company_name"] = sorted_df["company_name"].str[:40]
        ax.barh(sorted_df["company_name"], sorted_df["patent_count"],
                color="#38bdf8", edgecolor="none")
        ax.set_xlabel("Total Patents", color="#94a3b8")
        ax.tick_params(colors="#94a3b8", labelsize=9)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
        for spine in ax.spines.values():
            spine.set_edgecolor("#334155")
        ax.grid(axis="x", color="#334155", alpha=0.5)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close()

        st.divider()
        csv = df.to_csv()
        st.download_button("⬇️ Download as CSV", csv,
                           "top_companies.csv", "text/csv")


# ── PAGE: Trends ──────────────────────────────────────────────────────────────

elif page == "📈 Trends":
    st.title("📈 Patent Filing Trends")
    st.divider()

    trend_df = run_query("""
        SELECT p.year,
               COUNT(*) AS total_patents,
               COUNT(DISTINCT pi.inventor_id) AS unique_inventors,
               COUNT(DISTINCT pc.company_id)  AS unique_companies
        FROM patents p
        LEFT JOIN patent_inventor pi ON p.patent_id = pi.patent_id
        LEFT JOIN patent_company  pc ON p.patent_id = pc.patent_id
        WHERE p.year IS NOT NULL
        GROUP BY p.year ORDER BY p.year
    """)

    if not trend_df.empty:
        metric = st.selectbox("Select metric to display",
                              ["total_patents", "unique_inventors", "unique_companies"])
        st.line_chart(trend_df.set_index("year")[metric])
        st.divider()
        st.markdown("**Full data table**")
        st.dataframe(trend_df.set_index("year"), use_container_width=True)


# ── PAGE: Search Patents ──────────────────────────────────────────────────────

elif page == "🔍 Search Patents":
    st.title("🔍 Search Patents")
    st.divider()

    search_term = st.text_input("Search by keyword in title or abstract", 
                                 placeholder="e.g. artificial intelligence, battery, semiconductor")

    if search_term:
        df = run_query(f"""
            SELECT p.patent_id, p.title, p.year, p.abstract
            FROM patents p
            WHERE p.title    LIKE '%{search_term}%'
               OR p.abstract LIKE '%{search_term}%'
            LIMIT 50
        """)

        if df.empty:
            st.warning(f"No patents found for '{search_term}'")
        else:
            st.success(f"Found {len(df)} patents matching '{search_term}'")
            for _, row in df.iterrows():
                with st.expander(f"📄 {row['title']} ({row['year']})"):
                    st.markdown(f"**Patent ID:** {row['patent_id']}")
                    st.markdown(f"**Year:** {row['year']}")
                    st.markdown(f"**Abstract:** {row['abstract'][:500]}...")
    else:
        st.info("Type a keyword above to search through 500,000 patents")


# ── PAGE: Run SQL ─────────────────────────────────────────────────────────────

elif page == "🗄️ Run SQL":
    st.title("🗄️ Run Your Own SQL Query")
    st.markdown("Write any SQL query against the patents database and see results instantly")
    st.divider()

    st.markdown("**Available tables:** `patents`, `inventors`, `companies`, `patent_inventor`, `patent_company`")

    example_queries = {
        "Top 10 inventors": "SELECT i.name, COUNT(DISTINCT pi.patent_id) AS patents\nFROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id\nGROUP BY i.inventor_id ORDER BY patents DESC LIMIT 10",
        "Patents per year": "SELECT year, COUNT(*) AS total\nFROM patents WHERE year IS NOT NULL\nGROUP BY year ORDER BY year",
        "Top companies":    "SELECT c.name, COUNT(DISTINCT pc.patent_id) AS patents\nFROM companies c JOIN patent_company pc ON c.company_id = pc.company_id\nGROUP BY c.company_id ORDER BY patents DESC LIMIT 10",
        "Recent patents":   "SELECT patent_id, title, year FROM patents\nWHERE year = 2019 LIMIT 20",
    }

    selected = st.selectbox("Or pick an example query", ["Custom"] + list(example_queries.keys()))

    default_sql = example_queries.get(selected, "SELECT * FROM patents LIMIT 10")
    sql = st.text_area("SQL Query", value=default_sql, height=150)

    if st.button("▶️ Run Query", type="primary"):
        try:
            result = run_query(sql)
            st.success(f"Returned {len(result):,} rows")
            st.dataframe(result, use_container_width=True)

            if not result.empty:
                csv = result.to_csv(index=False)
                st.download_button("⬇️ Download results as CSV",
                                   csv, "query_results.csv", "text/csv")
        except Exception as e:
            st.error(f"Query error: {e}")

# ── Footer ────────────────────────────────────────────────────────────────────

st.sidebar.divider()
st.sidebar.markdown("*Built with Python, pandas, SQLite & Streamlit*")
st.sidebar.markdown("*Data: USPTO PatentsView*")