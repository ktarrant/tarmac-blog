"""Checks run against the real built data. Prints problems and exits
non-zero if any are found, so a bad refresh can't land silently.

Unit tests for the parsing logic live in tests/ and need no network.
"""

from __future__ import annotations

from datetime import date

import polars as pl

from . import transform
from .paths import YEARS
from .states import ABBRS, ABBRS_50

# Wikidata term boundaries disagree with each other by a few days where
# sources differ on the handover date. Anything longer is a real conflict.
BOUNDARY_TOLERANCE_DAYS = 30


def check_population(problems: list[str]) -> None:
    frame = transform.load_population()
    for abbr in ABBRS:
        years = set(frame.filter(pl.col("abbr") == abbr)["year"].to_list())
        missing = set(YEARS) - years
        if missing:
            problems.append(f"population: {abbr} missing years {sorted(missing)}")
    if (frame["population"] <= 0).any():
        problems.append("population: non-positive values present")


def check_deflator(problems: list[str]) -> None:
    frame = transform.load_deflator()
    missing = set(YEARS) - set(frame["year"].to_list())
    if missing:
        problems.append(f"deflator: missing years {sorted(missing)}")
    if not frame["deflator"].is_sorted():
        problems.append("deflator: series is not monotonically increasing")


def check_governors(problems: list[str]) -> None:
    frame = transform.load_governors().sort(["abbr", "start"])

    covered = set(frame["abbr"].to_list())
    missing_states = set(ABBRS_50) - covered
    if missing_states:
        problems.append(f"governors: no terms for {sorted(missing_states)}")

    unresolved = frame.filter(pl.col("party").is_null())
    for row in unresolved.to_dicts():
        problems.append(
            f"governors: {row['abbr']} {row['name']} ({row['start']}) has no resolved party "
            "— add a row to curated/governor_overrides.csv"
        )

    for abbr in sorted(covered):
        terms = frame.filter(pl.col("abbr") == abbr).to_dicts()
        for earlier, later in zip(terms, terms[1:]):
            if earlier["end"] is None or earlier["name"] == later["name"]:
                continue
            overlap = (date.fromisoformat(earlier["end"]) - date.fromisoformat(later["start"])).days
            if overlap > BOUNDARY_TOLERANCE_DAYS:
                problems.append(
                    f"governors: {abbr} {earlier['name']} overlaps {later['name']} by {overlap} days"
                )

        # Every year in range needs someone in office.
        for year in YEARS:
            reference = date(year, 7, 1)
            in_office = any(
                date.fromisoformat(t["start"]) <= reference
                and (t["end"] is None or date.fromisoformat(t["end"]) >= reference)
                for t in terms
            )
            if not in_office:
                problems.append(f"governors: {abbr} has nobody in office on {reference}")


def run() -> list[str]:
    problems: list[str] = []
    check_population(problems)
    check_deflator(problems)
    check_governors(problems)
    return problems


if __name__ == "__main__":
    import sys

    found = run()
    for problem in found:
        print(f"FAIL {problem}")
    print(f"\n{len(found)} problem(s)" if found else "\nall checks passed")
    sys.exit(1 if found else 0)
