# 🔬 Global Patent Intelligence Pipeline

> A coursework data engineering project that collects, cleans, stores, and analyses 
> real-world patent data from the USPTO PatentsView database.

---

## 📌 Project Overview

This pipeline processes millions of granted US patent records to answer questions like:
- **Who are the world's most prolific inventors?**
- **Which companies hold the most patents?**
- **Which countries drive global innovation?**
- **How has patent filing grown over time?**

**Data Source:** [USPTO PatentsView Bulk Data](https://data.uspto.gov/bulkdata/datasets/pvgpatdis)

---

## 🗂️ Project Structure

```
patent_pipeline/
│
├── run_pipeline.py            ← Master runner (runs all steps)
├── schema.sql                 ← Database schema (standalone)
├── requirements.txt
│
├── scripts/
│   ├── 01_download_data.py    ← Downloads TSV files from USPTO
│   ├── 02_clean_data.py       ← Cleans data with pandas
│   ├── 03_load_database.py    ← Loads into SQLite database
│   ├── 04_run_queries.py      ← All 7 SQL analytical queries
│   ├── 05_generate_reports.py ← Console + CSV + JSON reports
│   └── 06_visualize.py        ← 5 publication-quality charts
│
├── data/
│   ├── raw/                   ← Downloaded TSV files (gitignored)
│   └── clean/                 ← Cleaned CSV files
│       ├── clean_patents.csv
│       ├── clean_inventors.csv
│       ├── clean_companies.csv
│       ├── clean_patent_inventor.csv
│       └── clean_patent_company.csv
│
├── reports/
│   ├── top_inventors.csv
│   ├── top_companies.csv
│   ├── country_trends.csv
│   ├── yearly_trends.csv
│   └── summary.json
│
└── visualizations/
    ├── 01_top_companies.png
    ├── 02_top_countries.png
    ├── 03_yearly_trend.png
    ├── 04_top_inventors.png
    └── 05_country_share.png
```

---

## ⚡ Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/patent-intelligence-pipeline.git
cd patent-intelligence-pipeline
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the full pipeline
```bash
python run_pipeline.py
```

Or run steps individually:
```bash
python scripts/01_download_data.py    # Download raw data
python scripts/02_clean_data.py       # Clean with pandas
python scripts/03_load_database.py    # Build SQLite database
python scripts/04_run_queries.py      # Run SQL queries
python scripts/05_generate_reports.py # Generate reports
python scripts/06_visualize.py        # Create charts
```

---

## 🗄️ Database Schema

| Table | Description |
|-------|-------------|
| `patents` | patent_id, title, abstract, filing_date, year |
| `inventors` | inventor_id, name, country |
| `companies` | company_id, name |
| `patent_inventor` | patent_id ↔ inventor_id (many-to-many) |
| `patent_company` | patent_id ↔ company_id (many-to-many) |

---

## 📊 SQL Queries

| Query | Description | Technique |
|-------|-------------|-----------|
| Q1 | Top inventors by patent count | `GROUP BY`, `COUNT DISTINCT` |
| Q2 | Top companies by patent count | `GROUP BY`, `JOIN` |
| Q3 | Top countries with share % | `GROUP BY`, subquery |
| Q4 | Patent filings per year | `GROUP BY year` |
| Q5 | Patents + inventors + companies | Multi-table `JOIN` |
| Q6 | Top inventors at top-3 companies | `WITH` (CTE) |
| Q7 | Inventor rankings per country | `RANK()`, `DENSE_RANK()` window functions |

---

## 📁 Output Reports

### Console Report
A formatted terminal summary with patent counts, rankings, and an ASCII bar chart of yearly trends.

### CSV Reports
- `top_inventors.csv` — Top 20 inventors with country
- `top_companies.csv` — Top 20 patent-holding companies
- `country_trends.csv` — Patent counts and share per country
- `yearly_trends.csv` — Annual patent filing counts (1976–2025)

### JSON Report (`summary.json`)
```json
{
  "summary": { "total_patents": 8000000, "total_inventors": 3500000 },
  "top_inventors": [{"rank": 1, "name": "...", "patent_count": 312}],
  "top_companies": [{"rank": 1, "name": "IBM", "patent_count": 12000}],
  "top_countries": [{"country": "US", "share_%": 48.2}],
  "yearly_trends": [{"year": 2024, "total_patents": 350000}]
}
```

---

## 📈 Visualizations

Five charts are generated in `visualizations/`:
1. **Top 15 Companies** — Horizontal bar chart
2. **Top 15 Countries** — Bar chart with labels
3. **Filings Over Time** — Line chart with peak annotation
4. **Top 10 Inventors** — Dot plot with country labels
5. **Country Share** — Pie chart

---

## 🛠️ Technologies Used

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Core scripting |
| pandas | Data cleaning & transformation |
| SQLite | Local database storage |
| matplotlib / seaborn | Visualizations |
| requests + tqdm | Data download |

---

## 📌 Notes on Reproducibility

- Raw data files are **gitignored** (too large for GitHub). Run `01_download_data.py` to fetch them.
- The pipeline uses `nrows=None` by default (all data). Set `SAMPLE_SIZE = 500_000` in `02_clean_data.py` for faster local development.
- Python 3.10+ is required for the `tuple[...]` type hint syntax.

---

*Built as part of a Data Engineering coursework project.*
