"""Anomaly classification — telling real events apart from data artifacts.

Each case is modelled on a real one found in the data.
"""

from datetime import date

from state_budgets import anomalies

YEARS = list(range(2012, 2025))


def _flat(value: int) -> list[int]:
    return [value] * len(YEARS)


def _with(value: int, index: int, replacement: int) -> list[int]:
    series = _flat(value)
    series[index] = replacement
    return series


def test_a_spike_that_reverts_is_an_event():
    """Florida FY2023: 'other' spending trebled when Hurricane Ian hit, then
    fell back the next year."""
    series = {"expenditure.other": _with(7_000_000_000, 11, 20_000_000_000)}
    found = anomalies.detect(series, YEARS)

    assert [(a.year, a.kind) for a in found] == [(2023, "spike")]


def test_the_year_a_spike_reverts_is_not_reported_again():
    """Otherwise a hurricane produces a second finding reading 'spending
    collapsed 60%' when it only returned to normal."""
    series = {"expenditure.other": _with(7_000_000_000, 5, 20_000_000_000)}
    found = anomalies.detect(series, YEARS)

    assert len(found) == 1
    assert found[0].year == YEARS[5]


def test_offsetting_moves_in_one_year_are_a_suspected_coding_error():
    """Massachusetts FY2014 booked billions of K-12 as administration and put
    it back the next year."""
    series = {
        "expenditure.k12": _with(5_400_000_000, 2, 1_000_000_000),
        "expenditure.administration": _with(3_600_000_000, 2, 10_300_000_000),
    }
    found = anomalies.detect(series, YEARS)

    assert {a.kind for a in found} == {"suspected_coding_error"}


def test_opposite_moves_in_different_flows_are_not_a_coding_error():
    """Debt issuance falling while a tax rises is a coincidence — money did not
    move between those lines."""
    series = {
        "debt.issued": _with(2_400_000_000, 2, 1_300_000_000),
        "revenue.taxes": _with(3_000_000_000, 2, 4_200_000_000),
    }
    found = anomalies.detect(series, YEARS)

    assert "suspected_coding_error" not in {a.kind for a in found}


def test_a_permanent_step_in_2022_is_attributed_to_the_schema_change():
    series = {"expenditure.administration": [9_000_000_000] * 10 + [24_900_000_000] * 3}
    found = anomalies.detect(series, YEARS)

    assert [(a.year, a.kind) for a in found] == [(2022, "census_schema_change")]


def test_a_permanent_step_in_another_year_is_a_level_shift():
    """Nevada FY2023 raised school funding and it stayed raised."""
    series = {"expenditure.k12": [3_700_000_000] * 11 + [7_300_000_000] * 2}
    found = anomalies.detect(series, YEARS)

    assert [(a.year, a.kind) for a in found] == [(2023, "level_shift")]


def test_small_moves_are_ignored_however_large_the_percentage():
    series = {"expenditure.parks_and_recreation": _with(10_000_000, 4, 30_000_000)}
    assert anomalies.detect(series, YEARS) == []


def test_impact_ranks_by_share_of_the_whole_budget():
    """A big percentage move in a small line must rank below a smaller move in
    a large one, or the list is dominated by trivia."""
    series = {
        "expenditure.parks_and_recreation": _with(500_000_000, 4, 1_500_000_000),
        "expenditure.public_welfare": _with(40_000_000_000, 4, 60_000_000_000),
    }
    budget = [100_000_000_000] * len(YEARS)
    found = anomalies.detect(series, YEARS, budget)

    assert found[0].metric == "expenditure.public_welfare"
    assert found[0].impact > found[1].impact


def test_fiscal_year_follows_each_state_start_month():
    """Hurricane Ian made landfall in September 2022. That is FY2023 in Florida,
    which starts its year in July, but still FY2022 in Texas, which starts in
    September... and Texas's own year had just turned over."""
    ian = date(2022, 9, 29)
    assert anomalies.fiscal_year("FL", ian) == 2023
    assert anomalies.fiscal_year("NY", ian) == 2023
    assert anomalies.fiscal_year("AL", ian) == 2022

    # A June event falls in the fiscal year already under way almost everywhere.
    june = date(2022, 6, 15)
    assert anomalies.fiscal_year("FL", june) == 2022
    assert anomalies.fiscal_year("NY", june) == 2023
