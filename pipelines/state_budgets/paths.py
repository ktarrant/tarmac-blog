"""Repo paths and the year range the investigation covers."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_DIR = REPO_ROOT / "public" / "data" / "state-budgets"
CURATED_DIR = Path(__file__).resolve().parent / "curated"

# 2000-2024. The start is set by population estimates and the recessions the
# article shades (2001, 2008-09, 2020); Census finance data itself goes back
# to 1967 if the range is ever extended.
START_YEAR = 2000
END_YEAR = 2024
YEARS = range(START_YEAR, END_YEAR + 1)
