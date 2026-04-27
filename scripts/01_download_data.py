"""
============================================================
  Global Patent Intelligence Pipeline
  Step 1: Data Downloader
  Source: PatentsView Granted Patent Disambiguated Data
  https://data.uspto.gov/bulkdata/datasets/pvgpatdis
============================================================

This script downloads the core TSV files from PatentsView.
We pull a recent yearly snapshot so the dataset stays manageable.

Files downloaded:
  - g_patent.tsv          → patent titles, abstracts, dates
  - g_inventor_disambiguated.tsv  → inventor names & countries
  - g_assignee_disambiguated.tsv  → company (assignee) info
  - g_patent_inventor.tsv → links patents ↔ inventors
  - g_patent_assignee.tsv → links patents ↔ companies
"""

import os
import requests
import zipfile
from tqdm import tqdm

# ── Configuration ────────────────────────────────────────────────────────────

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# PatentsView bulk data base URL (yearly snapshots, most recent stable year)
BASE_URL = "https://data.uspto.gov/bulkdata/datasets/pvgpatdis/files"

# Files we need — adjust the date tag to match what's on the USPTO page
FILES = {
    "g_patent.tsv.zip":                        "Core patent records (title, abstract, date)",
    "g_inventor_disambiguated.tsv.zip":         "Disambiguated inventor names & countries",
    "g_assignee_disambiguated.tsv.zip":         "Company / assignee records",
    "g_patent_inventor.tsv.zip":               "Patent ↔ Inventor relationships",
    "g_patent_assignee.tsv.zip":               "Patent ↔ Company relationships",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def download_file(url: str, dest_path: str) -> bool:
    """Stream-download a file with a progress bar."""
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        filename = os.path.basename(dest_path)

        with open(dest_path, "wb") as f, tqdm(
            desc=f"  Downloading {filename}",
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
        return True

    except requests.RequestException as e:
        print(f"  ✗ Failed to download {url}: {e}")
        return False


def extract_zip(zip_path: str, dest_dir: str) -> None:
    """Unzip a downloaded file into dest_dir."""
    print(f"  Extracting {os.path.basename(zip_path)} …")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    os.remove(zip_path)   # remove zip after extraction to save space


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Global Patent Intelligence — Data Downloader")
    print("  Source: USPTO PatentsView Bulk Data")
    print("=" * 60 + "\n")

    for filename, description in FILES.items():
        url = f"{BASE_URL}/{filename}"
        zip_dest = os.path.join(RAW_DIR, filename)
        tsv_name = filename.replace(".zip", "")
        tsv_dest = os.path.join(RAW_DIR, tsv_name)

        # Skip if already downloaded & extracted
        if os.path.exists(tsv_dest):
            size_mb = os.path.getsize(tsv_dest) / 1_000_000
            print(f"  ✓ {tsv_name} already exists ({size_mb:.1f} MB) — skipping")
            continue

        print(f"\n  → {description}")
        if download_file(url, zip_dest):
            extract_zip(zip_dest, RAW_DIR)
            print(f"  ✓ Saved to {tsv_dest}")

    print("\n" + "=" * 60)
    print("  Download complete! Raw files are in data/raw/")
    print("  Next step: run scripts/02_clean_data.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
