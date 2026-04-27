-- ============================================================
--   Global Patent Intelligence Pipeline
--   schema.sql — Database Schema
--   Source: USPTO PatentsView Granted Patent Disambiguated Data
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ────────────────────────────────────────────────────────────
-- Core Tables
-- ────────────────────────────────────────────────────────────

-- Core patent records
CREATE TABLE IF NOT EXISTS patents (
    patent_id   TEXT PRIMARY KEY,      -- USPTO patent identifier
    title       TEXT NOT NULL,         -- Patent title
    abstract    TEXT,                  -- Patent abstract (max 2000 chars)
    filing_date TEXT,                  -- Grant date (ISO 8601: YYYY-MM-DD)
    year        INTEGER                -- Extracted year for fast aggregation
);

-- Disambiguated inventor records (PatentsView disambiguation applied)
CREATE TABLE IF NOT EXISTS inventors (
    inventor_id TEXT PRIMARY KEY,      -- Disambiguated inventor ID
    name        TEXT NOT NULL,         -- Full name (Title Case)
    country     TEXT DEFAULT 'Unknown' -- ISO 2-letter country code or 'Unknown'
);

-- Company / assignee records
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,       -- Disambiguated assignee ID
    name       TEXT NOT NULL           -- Organisation name
);

-- ────────────────────────────────────────────────────────────
-- Relationship Tables
-- ────────────────────────────────────────────────────────────

-- Many-to-many: a patent can have multiple inventors
CREATE TABLE IF NOT EXISTS patent_inventor (
    patent_id   TEXT NOT NULL,
    inventor_id TEXT NOT NULL,
    PRIMARY KEY (patent_id, inventor_id),
    FOREIGN KEY (patent_id)   REFERENCES patents(patent_id),
    FOREIGN KEY (inventor_id) REFERENCES inventors(inventor_id)
);

-- Many-to-many: a patent can have multiple assignees
CREATE TABLE IF NOT EXISTS patent_company (
    patent_id  TEXT NOT NULL,
    company_id TEXT NOT NULL,
    PRIMARY KEY (patent_id, company_id),
    FOREIGN KEY (patent_id)  REFERENCES patents(patent_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- ────────────────────────────────────────────────────────────
-- Indexes for Analytical Query Performance
-- ────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_patents_year      ON patents(year);
CREATE INDEX IF NOT EXISTS idx_inventors_country ON inventors(country);
CREATE INDEX IF NOT EXISTS idx_pi_patent         ON patent_inventor(patent_id);
CREATE INDEX IF NOT EXISTS idx_pi_inventor       ON patent_inventor(inventor_id);
CREATE INDEX IF NOT EXISTS idx_pc_patent         ON patent_company(patent_id);
CREATE INDEX IF NOT EXISTS idx_pc_company        ON patent_company(company_id);

-- ────────────────────────────────────────────────────────────
-- Sample Analytical Queries
-- ────────────────────────────────────────────────────────────

-- Q1: Top Inventors
-- SELECT i.name, i.country, COUNT(DISTINCT pi.patent_id) AS patents
-- FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
-- GROUP BY i.inventor_id ORDER BY patents DESC LIMIT 20;

-- Q2: Top Companies
-- SELECT c.name, COUNT(DISTINCT pc.patent_id) AS patents
-- FROM companies c JOIN patent_company pc ON c.company_id = pc.company_id
-- GROUP BY c.company_id ORDER BY patents DESC LIMIT 20;

-- Q3: Top Countries
-- SELECT i.country, COUNT(DISTINCT pi.patent_id) AS patents
-- FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
-- WHERE i.country != 'Unknown'
-- GROUP BY i.country ORDER BY patents DESC LIMIT 30;

-- Q4: Trends Over Time
-- SELECT year, COUNT(*) AS total_patents
-- FROM patents WHERE year IS NOT NULL
-- GROUP BY year ORDER BY year;

-- Q7: Rank inventors by country (window function)
-- SELECT name, country, COUNT(*) AS patents,
--        RANK() OVER (PARTITION BY country ORDER BY COUNT(*) DESC) AS country_rank
-- FROM inventors i JOIN patent_inventor pi ON i.inventor_id = pi.inventor_id
-- GROUP BY i.inventor_id;
