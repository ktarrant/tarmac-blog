"""Repo paths and the year range the investigation covers."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_DIR = REPO_ROOT / "public" / "data" / "state-budgets"
CURATED_DIR = Path(__file__).resolve().parent / "curated"

# 2012-2024. The Census API catalog advertises 1967-2024 for state finances but
# answers 204 No Content for every year before 2012, so 2012 is the real floor.
# Of the recessions the article planned to shade, only 2020 falls in range.
START_YEAR = 2012
END_YEAR = 2024
YEARS = range(START_YEAR, END_YEAR + 1)

# Census redefined its published totals between FY2021 and FY2022: through 2021
# they include insurance-trust flows, from 2022 they don't, and the API carries
# far more item-code detail before the change. The pipeline therefore computes
# its own totals on one definition across all years (general revenue and
# expenditure, insurance trust reported separately) and reconciles them exactly
# against the published figures for the years where the definitions agree.
PUBLISHED_TOTALS_COMPARABLE_FROM = 2022
