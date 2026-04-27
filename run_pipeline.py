"""
============================================================
  Global Patent Intelligence Pipeline
  run_pipeline.py — Master Runner
============================================================

Runs all pipeline steps in order:
  1. Download raw data     (01_download_data.py)
  2. Clean with pandas     (02_clean_data.py)
  3. Load into SQLite DB   (03_load_database.py)
  4. Run SQL queries       (04_run_queries.py)
  5. Generate reports      (05_generate_reports.py)
  6. Create visualizations (06_visualize.py)

Usage:
  python run_pipeline.py           # full pipeline
  python run_pipeline.py --skip-download   # skip step 1 if data already exists
"""

import os
import sys
import time
import argparse
import subprocess

BASE    = os.path.dirname(__file__)
SCRIPTS = os.path.join(BASE, "scripts")

STEPS = [
    ("01_download_data.py",    "Downloading raw data from USPTO PatentsView"),
    ("02_clean_data.py",       "Cleaning data with pandas"),
    ("03_load_database.py",    "Loading clean data into SQLite"),
    ("04_run_queries.py",      "Running SQL analytical queries"),
    ("05_generate_reports.py", "Generating Console / CSV / JSON reports"),
    ("06_visualize.py",        "Creating visualizations"),
]


def run_step(script: str, description: str) -> bool:
    path = os.path.join(SCRIPTS, script)
    print(f"\n{'─'*60}")
    print(f"  {description}")
    print(f"  Script: scripts/{script}")
    print(f"{'─'*60}")

    t0 = time.time()
    result = subprocess.run([sys.executable, path], cwd=BASE)
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"\n  ✗ Step failed (exit code {result.returncode})")
        return False

    print(f"\n  ✓ Completed in {elapsed:.1f}s")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run the patent data pipeline")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip the download step if raw data already exists")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(f"{'GLOBAL PATENT INTELLIGENCE PIPELINE':^60}")
    print(f"{'Full end-to-end run':^60}")
    print("=" * 60)

    total_start = time.time()
    failed      = False

    for script, description in STEPS:
        if args.skip_download and script == "01_download_data.py":
            print(f"\n  ⏩ Skipping {script} (--skip-download flag)")
            continue

        if not run_step(script, description):
            failed = True
            print("\n  Pipeline halted due to error.")
            break

    elapsed = time.time() - total_start
    print("\n" + "=" * 60)
    if failed:
        print(f"  Pipeline FAILED  (elapsed: {elapsed:.1f}s)")
    else:
        print(f"  Pipeline COMPLETE  (total time: {elapsed:.1f}s)")
        print()
        print("  Outputs:")
        print("    data/clean/          — cleaned CSV files")
        print("    patents.db           — SQLite database")
        print("    reports/             — CSV, JSON reports")
        print("    visualizations/      — PNG charts")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
