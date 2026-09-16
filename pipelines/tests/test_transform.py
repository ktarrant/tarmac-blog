"""Parsing tests against small fixtures — no network, so CI can run them."""

import json

from state_budgets import transform


def test_resolve_party_uses_the_single_known_party():
    row = {"abbr": "TX", "name": "Ann Richards", "start": "1991-01-15", "parties": ["D"]}
    assert transform._resolve_party(row, {}) == "D"


def test_resolve_party_returns_none_when_wikidata_gives_several():
    """A party-switcher has one row per party; without an override we can't
    tell which they held in office, and validate.py must flag it."""
    row = {"abbr": "TX", "name": "Rick Perry", "start": "2000-12-21", "parties": ["D", "R"]}
    assert transform._resolve_party(row, {}) is None


def test_override_wins_over_ambiguous_wikidata_parties():
    row = {"abbr": "TX", "name": "Rick Perry", "start": "2000-12-21", "parties": ["D", "R"]}
    overrides = {("TX", "Rick Perry", "2000-12-21"): "R"}
    assert transform._resolve_party(row, overrides) == "R"


def test_deflator_is_rebased_so_the_last_year_is_one(tmp_path):
    path = tmp_path / "deflator.csv"
    path.write_text(
        "observation_date,A191RD3A086NBEA\n"
        "2012-01-01,50.0\n"
        "2023-01-01,75.0\n"
        "2024-01-01,100.0\n"
    )
    frame = transform.load_deflator(path)
    assert frame["deflator"].to_list() == [0.5, 0.75, 1.0]


def test_population_prefers_the_newer_file_at_overlapping_years(tmp_path):
    newer = tmp_path / "newer.csv"
    newer.write_text("STATE,NAME,POPESTIMATE2020\n06,California,39000000\n")
    older = tmp_path / "older.csv"
    older.write_text("STATE,NAME,POPESTIMATE2020\n06,California,11111111\n")

    frame = transform.load_population([newer, older])
    assert frame.to_dicts() == [{"abbr": "CA", "year": 2020, "population": 39000000}]


def test_population_skips_the_age_and_sex_breakdown_rows(tmp_path):
    """The 2000s intercensal file repeats each state per sex/age group; only
    the all-zero total row is a state total."""
    path = tmp_path / "intercensal.csv"
    path.write_text(
        "STATE,NAME,SEX,ORIGIN,RACE,AGEGRP,POPESTIMATE2015\n"
        "06,California,0,0,0,0,35000000\n"
        "06,California,1,0,0,3,900000\n"
    )
    frame = transform.load_population([path])
    assert frame.to_dicts() == [{"abbr": "CA", "year": 2015, "population": 35000000}]


def test_governors_drops_terms_without_a_start_date(tmp_path):
    path = tmp_path / "governors.json"
    path.write_text(
        json.dumps(
            {
                "results": {
                    "bindings": [
                        {
                            "stateLabel": {"value": "Texas"},
                            "personLabel": {"value": "Greg Abbott"},
                            "partyLabel": {"value": "Republican Party"},
                            "start": {"value": "2015-01-20T00:00:00Z"},
                        },
                        {
                            "stateLabel": {"value": "Texas"},
                            "personLabel": {"value": "Undated Person"},
                            "partyLabel": {"value": "Democratic Party"},
                        },
                    ]
                }
            }
        )
    )
    frame = transform.load_governors(path)
    assert frame["name"].to_list() == ["Greg Abbott"]
    assert frame["party"].to_list() == ["R"]
    assert frame["end"].to_list() == [None]
