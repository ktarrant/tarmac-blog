"""Checks run against the real built data. Prints problems and exits
non-zero if any are found, so a bad refresh can't land silently.

Unit tests for the parsing logic live in tests/ and need no network.
"""

from __future__ import annotations

from datetime import date

import polars as pl

from . import transform
from .paths import PUBLISHED_TOTALS_COMPARABLE_FROM, YEARS
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

    # A bare Q-id means Wikidata's label service found no label in any of the
    # languages we ask for, and the name would render as "Q2685" on the page.
    for row in frame.filter(pl.col("name").str.contains(r"^Q\d+$")).to_dicts():
        problems.append(
            f"governors: {row['abbr']} {row['start']} has an unresolved Wikidata id "
            f"({row['name']}) instead of a name"
        )

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


def check_finances(problems: list[str]) -> None:
    finances = transform.load_finances()
    published = transform.load_published_totals()

    for abbr in ABBRS_50:
        years = set(finances.filter(pl.col("abbr") == abbr)["year"].to_list())
        missing = set(YEARS) - years
        if missing:
            problems.append(f"finances: {abbr} missing years {sorted(missing)}")

    totals = (
        finances.filter(pl.col("flow").is_in(["revenue", "expenditure"]))
        .group_by(["abbr", "year", "flow"])
        .agg(pl.col("amount").sum())
    )

    # Summing the detail item codes must reproduce Census's published totals
    # exactly, for the years whose definitions match ours. This is what catches
    # a miscategorized item code.
    comparable = totals.join(published, on=["abbr", "year", "flow"], how="inner").filter(
        pl.col("year") >= PUBLISHED_TOTALS_COMPARABLE_FROM
    )
    mismatched = comparable.filter(pl.col("amount") != pl.col("published"))
    for row in mismatched.head(10).to_dicts():
        share = (row["amount"] - row["published"]) / row["published"] if row["published"] else float("inf")
        problems.append(
            f"finances: {row['abbr']} {row['year']} {row['flow']} sums to {row['amount']:,} "
            f"but Census publishes {row['published']:,} ({share:+.3%})"
        )
    if mismatched.height > 10:
        problems.append(f"finances: ...and {mismatched.height - 10} more total mismatches")

    expected = len(ABBRS_50) * len([y for y in YEARS if y >= PUBLISHED_TOTALS_COMPARABLE_FROM]) * 2
    if comparable.height < expected:
        problems.append(
            f"finances: only {comparable.height} state-year-flow totals could be checked "
            f"against published figures, expected {expected}"
        )

    # Debt outstanding has its own published total and its own way of going
    # wrong: it is reported in two tracks (conduit debt issued for private
    # borrowers, and the state's own debt) that must be added, and summing only
    # one silently understates every state.
    debt_totals = (
        finances.filter((pl.col("flow") == "debt") & (pl.col("component") == "outstanding_end"))
        .group_by(["abbr", "year"])
        .agg(pl.col("amount").sum())
        .with_columns(pl.lit("debt_outstanding").alias("flow"))
    )
    debt_check = debt_totals.join(published, on=["abbr", "year", "flow"], how="inner")
    debt_bad = debt_check.filter(pl.col("amount") != pl.col("published"))
    for row in debt_bad.head(5).to_dicts():
        share = (row["amount"] - row["published"]) / row["published"] if row["published"] else 0
        problems.append(
            f"finances: {row['abbr']} {row['year']} debt outstanding sums to {row['amount']:,} "
            f"but Census publishes {row['published']:,} ({share:+.3%})"
        )
    if debt_bad.height > 5:
        problems.append(f"finances: ...and {debt_bad.height - 5} more debt total mismatches")
    if debt_check.height < len(ABBRS_50) * len(YEARS):
        problems.append(
            f"finances: only {debt_check.height} state-years of debt could be checked "
            f"against published totals, expected {len(ABBRS_50) * len(YEARS)}"
        )

    # Earlier years can't be checked against published totals (see paths.py), so
    # check the series is continuous instead: a mapping that silently dropped
    # codes in one era would show up as a step change here.
    national = (
        totals.group_by(["year", "flow"]).agg(pl.col("amount").sum()).sort(["flow", "year"])
    )
    for flow in ("revenue", "expenditure"):
        series = national.filter(pl.col("flow") == flow).sort("year")
        amounts = series["amount"].to_list()
        for year, before, after in zip(series["year"].to_list()[1:], amounts, amounts[1:]):
            change = (after - before) / before
            if not -0.10 < change < 0.25:
                problems.append(
                    f"finances: national {flow} moved {change:+.1%} into {year} — "
                    "implausible for a real fiscal year, suspect a mapping break"
                )


def run() -> list[str]:
    problems: list[str] = []
    check_population(problems)
    check_deflator(problems)
    check_governors(problems)
    check_finances(problems)
    return problems


if __name__ == "__main__":
    import sys

    found = run()
    for problem in found:
        print(f"FAIL {problem}")
    print(f"\n{len(found)} problem(s)" if found else "\nall checks passed")
    sys.exit(1 if found else 0)
