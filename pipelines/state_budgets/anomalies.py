"""Finds year-over-year jumps in a state's budget and says what kind each is.

Three very different things produce a jump that looks identical on a chart, so
the point of this module is to tell them apart rather than to find them:

- a Census coding error, where money moves between functions for one year and
  moves back (Massachusetts FY2014 booked $4.5B of K-12 as administration);
- the FY2022 restructuring, where Census collapsed item-code detail and some
  functions step to a new level permanently;
- an actual event, where spending rises and then falls back.

Anything not confidently explained is reported as unexplained. Presenting a
coding error as a policy decision is the failure mode worth avoiding.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from datetime import date
from functools import cache
from pathlib import Path

CURATED = Path(__file__).resolve().parent / "curated"

# A jump must clear both a relative and an absolute bar: 35% of a small function
# is noise, and $200M of a large one is rounding.
RELATIVE_THRESHOLD = 0.35
ABSOLUTE_THRESHOLD = 200_000_000

# Census restructured its item codes for FY2022; a level shift at exactly this
# year is attributed to that rather than to anything a state did.
SCHEMA_CHANGE_YEAR = 2022


@dataclass
class Anomaly:
    year: int
    metric: str
    previous: int
    amount: int
    change: float
    kind: str
    # How much the move was worth against the state's whole budget that year.
    # A 90% jump in a small line barely registers; this is what makes a list of
    # anomalies rankable into "what actually moved the budget".
    impact: float = 0.0


@cache
def fiscal_year_starts() -> dict[str, int]:
    with (CURATED / "fiscal_years.csv").open(newline="") as f:
        return {row["abbr"]: int(row["fy_start_month"]) for row in csv.DictReader(f)}


def fiscal_year(abbr: str, when: date) -> int:
    """The state fiscal year a date falls in.

    A fiscal year is named for the calendar year it ends in, so a hurricane in
    September 2022 lands in FY2023 for the 46 states whose year starts in July.
    """
    start_month = fiscal_year_starts().get(abbr, 7)
    return when.year + 1 if when.month >= start_month else when.year


def _reverts(series: list[int], index: int) -> bool:
    """True if the move at `index` is undone by the following year."""
    if index + 1 >= len(series):
        return False
    rise = series[index] - series[index - 1]
    fall = series[index + 1] - series[index]
    return rise * fall < 0 and abs(fall) >= 0.6 * abs(rise)


def _is_offsetting(series_by_metric: dict[str, list[int]], index: int, metric: str) -> bool:
    """True if another line in the same flow moved the opposite way by a similar
    amount in the same year, which is the signature of money booked to the wrong
    line. Only lines within a flow are compared: debt issuance falling while some
    unrelated tax rises is a coincidence, not a miscoding."""
    flow = metric.split(".", 1)[0]
    move = series_by_metric[metric][index] - series_by_metric[metric][index - 1]
    for other, series in series_by_metric.items():
        if other == metric or not other.startswith(f"{flow}."):
            continue
        counter = series[index] - series[index - 1]
        if counter * move < 0 and abs(counter) >= 0.5 * abs(move) and _reverts(series, index):
            return True
    return False


def detect(
    series_by_metric: dict[str, list[int]],
    years: list[int],
    budget_by_year: list[int] | None = None,
) -> list[Anomaly]:
    """Every jump in a state's series, classified and ranked by impact."""
    found: list[Anomaly] = []

    for metric, series in series_by_metric.items():
        # A spike is two jumps — up, then back down. Reporting the second as its
        # own anomaly reads as "spending collapsed" when it only returned to
        # normal, so the year after a spike is skipped.
        settled_after: int | None = None

        for index in range(1, len(series)):
            if settled_after == index:
                continue
            previous, amount = series[index - 1], series[index]
            if previous <= 0:
                continue
            change = (amount - previous) / previous
            if abs(change) < RELATIVE_THRESHOLD or abs(amount - previous) < ABSOLUTE_THRESHOLD:
                continue

            year = years[index]
            reverts = _reverts(series, index)

            if _is_offsetting(series_by_metric, index, metric) and reverts:
                kind = "suspected_coding_error"
            elif year == SCHEMA_CHANGE_YEAR and not reverts:
                kind = "census_schema_change"
            elif reverts:
                kind = "spike"
            else:
                kind = "level_shift"

            if reverts:
                settled_after = index + 1

            budget = (budget_by_year or [])[index] if budget_by_year else 0
            impact = abs(amount - previous) / budget if budget else 0.0

            found.append(
                Anomaly(
                    year=year,
                    metric=metric,
                    previous=previous,
                    amount=amount,
                    change=round(change, 4),
                    kind=kind,
                    impact=round(impact, 5),
                )
            )

    return sorted(found, key=lambda a: -a.impact)


def as_dicts(found: list[Anomaly]) -> list[dict]:
    return [asdict(a) for a in found]
