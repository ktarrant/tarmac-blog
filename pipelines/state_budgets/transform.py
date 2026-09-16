"""Parse raw sources into tidy tables keyed by state and year, then write
the JSON the site reads from public/data/state-budgets/.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import polars as pl

from . import anomalies, categories, fetch
from .paths import END_YEAR, OUT_DIR, RAW_DIR, REPO_ROOT, START_YEAR, YEARS
from .states import ABBRS, ABBRS_50, NAME_BY_ABBR, STATES

# Wikidata reports party membership over a person's whole career, so a
# party-switcher yields one row per party. These labels are normalized and
# conflicts resolved against curated/governor_overrides.csv.
PARTY_NORMALIZATION = {
    "Democratic Party": "D",
    "Republican Party": "R",
    "New Hampshire Republican State Committee": "R",
    "New Hampshire Democratic Party": "D",
    "independent politician": "I",
    "Independent": "I",
}


def load_population(paths: list[Path] | None = None) -> pl.DataFrame:
    """Annual state population estimates, long format: abbr, year, population.

    Files are read newest-first so a later decade file wins at boundary years.
    """
    name_to_abbr = {name: abbr for _, (abbr, name) in STATES.items()}
    rows: list[dict] = []

    for path in paths if paths is not None else fetch.population():
        with path.open(newline="", encoding="latin-1") as f:
            reader = csv.DictReader(f)
            for record in reader:
                # The 2000s file breaks population out by sex/origin/race/age;
                # every other file is already a state total.
                if any(record.get(k, "0") != "0" for k in ("SEX", "ORIGIN", "RACE", "AGEGRP")):
                    continue
                abbr = name_to_abbr.get(record["NAME"])
                if abbr is None:
                    continue
                for column, value in record.items():
                    if not column.startswith("POPESTIMATE"):
                        continue
                    year = int(column.removeprefix("POPESTIMATE"))
                    if year in YEARS:
                        rows.append({"abbr": abbr, "year": year, "population": int(value)})

    # Decade files overlap at boundary years; the newer file wins.
    return (
        pl.DataFrame(rows)
        .unique(subset=["abbr", "year"], keep="first")
        .sort(["abbr", "year"])
    )


def load_finances(years: range | None = None) -> pl.DataFrame:
    """State government finances, long format: abbr, year, flow, function,
    component, item_code, amount (dollars).

    The API returns both detail item codes and Census's own published
    aggregates (ITEM_CODE 'AGG'); only the detail is kept, since summing it
    reproduces the published totals exactly (see validate.py) while also
    supporting the functional breakdowns the aggregates don't provide.
    """
    abbr_by_fips = {fips: abbr for fips, (abbr, _) in STATES.items()}
    rows: list[dict] = []

    for year in years if years is not None else YEARS:
        payload = json.loads(fetch.state_finances(year).read_text())
        header, *records = payload
        for record in records:
            field = dict(zip(header, record))
            item_code = field["ITEM_CODE"]
            if item_code == "AGG":
                continue
            classified = categories.classify(item_code)
            if classified is None:
                continue
            abbr = abbr_by_fips.get(field["state"])
            if abbr is None:
                continue
            rows.append(
                {
                    "abbr": abbr,
                    "year": year,
                    "item_code": item_code,
                    # Census reports thousands of dollars.
                    "amount": int(field["AMOUNT"]) * 1000,
                    **classified,
                }
            )

    # purpose is null for everything except debt, and the debt rows sort late
    # enough that inferring the column type from the first rows picks Null.
    return pl.DataFrame(rows, schema_overrides={"purpose": pl.Utf8}).sort(
        ["abbr", "year", "item_code"]
    )


def load_published_totals(years: range | None = None) -> pl.DataFrame:
    """Census's own published totals, used to check the detail sums up."""
    abbr_by_fips = {fips: abbr for fips, (abbr, _) in STATES.items()}
    wanted = {"SF0001": "revenue", "SF0132": "expenditure", "SF0455": "debt_outstanding"}
    rows: list[dict] = []

    for year in years if years is not None else YEARS:
        payload = json.loads(fetch.state_finances(year).read_text())
        header, *records = payload
        for record in records:
            field = dict(zip(header, record))
            flow = wanted.get(field["AGG_DESC"])
            if field["ITEM_CODE"] != "AGG" or flow is None:
                continue
            abbr = abbr_by_fips.get(field["state"])
            if abbr is None:
                continue
            rows.append(
                {"abbr": abbr, "year": year, "flow": flow, "published": int(field["AMOUNT"]) * 1000}
            )

    return pl.DataFrame(rows).sort(["abbr", "year", "flow"])


def load_deflator(path: Path | None = None) -> pl.DataFrame:
    """Annual GDP price deflator, rebased so the most recent year equals 1.0."""
    path = path if path is not None else fetch.gdp_deflator()
    rows = []
    with path.open(newline="") as f:
        for record in csv.DictReader(f):
            year = int(record["observation_date"][:4])
            value = record["A191RD3A086NBEA"]
            if year in YEARS and value not in (".", ""):
                rows.append({"year": year, "deflator": float(value)})

    frame = pl.DataFrame(rows).sort("year")
    base = frame["deflator"][-1]
    return frame.with_columns((pl.col("deflator") / base).alias("deflator"))


def load_governors(path: Path | None = None) -> pl.DataFrame:
    """Governor terms: abbr, name, party, start, end (end null if in office)."""
    payload = json.loads((path if path is not None else fetch.governors()).read_text())
    name_to_abbr = {name: abbr for _, (abbr, name) in STATES.items()}
    overrides = _governor_overrides()

    rows: list[dict] = []
    for binding in payload["results"]["bindings"]:
        get = lambda key: binding.get(key, {}).get("value")  # noqa: E731
        abbr = name_to_abbr.get(get("stateLabel") or "")
        if abbr is None:
            continue
        rows.append(
            {
                "abbr": abbr,
                "name": get("personLabel"),
                "party": PARTY_NORMALIZATION.get(get("partyLabel") or ""),
                "start": (get("start") or "")[:10] or None,
                "end": (get("end") or "")[:10] or None,
            }
        )

    frame = pl.DataFrame(rows, schema={"abbr": pl.Utf8, "name": pl.Utf8, "party": pl.Utf8, "start": pl.Utf8, "end": pl.Utf8})
    frame = frame.filter(pl.col("start").is_not_null())

    # One row per term. A party-switcher has several party values for the same
    # term; prefer the curated override, else the single known party.
    frame = (
        frame.group_by(["abbr", "name", "start", "end"])
        .agg(pl.col("party").drop_nulls().unique().alias("parties"))
        .with_columns(
            pl.struct(["abbr", "name", "start", "parties"])
            .map_elements(lambda row: _resolve_party(row, overrides), return_dtype=pl.Utf8)
            .alias("party")
        )
        .drop("parties")
        .sort(["abbr", "start"])
    )
    return frame


def _governor_overrides() -> dict[tuple[str, str, str], str]:
    path = Path(__file__).resolve().parent / "curated" / "governor_overrides.csv"
    if not path.exists():
        return {}
    with path.open(newline="") as f:
        return {
            (r["abbr"], r["name"], r["start"]): r["party"]
            for r in csv.DictReader(f)
            if not r["abbr"].startswith("#")
        }


def _resolve_party(row: dict, overrides: dict[tuple[str, str, str], str]) -> str | None:
    override = overrides.get((row["abbr"], row["name"], row["start"]))
    if override:
        return override
    parties = row["parties"]
    return parties[0] if len(parties) == 1 else None


def write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=False))
    return path


def build_politics() -> Path:
    """politics.json: governor terms per state."""
    governors = load_governors()
    payload = {
        "governors": {
            abbr: [
                {k: v for k, v in term.items() if k != "abbr"}
                for term in governors.filter(pl.col("abbr") == abbr).to_dicts()
            ]
            for abbr in ABBRS
        },
        "states": {abbr: NAME_BY_ABBR[abbr] for abbr in ABBRS},
    }
    return write_json(OUT_DIR / "politics.json", payload)


def load_disasters() -> dict[str, dict[int, list[dict]]]:
    """FEMA disasters keyed by state and the state fiscal year they fall in."""
    declarations = json.loads(fetch.disasters(START_YEAR).read_text())
    amounts_by_number = {
        record["disasterNumber"]: record
        for record in json.loads(
            fetch.disaster_amounts(sorted({d["disasterNumber"] for d in declarations})).read_text()
        )
    }

    by_state: dict[str, dict[int, list[dict]]] = {}
    for record in declarations:
        abbr = record["state"]
        if abbr not in NAME_BY_ABBR:
            continue
        declared = date.fromisoformat(record["declarationDate"][:10])
        year = anomalies.fiscal_year(abbr, declared)
        if year not in YEARS:
            continue
        summary = amounts_by_number.get(record["disasterNumber"], {})
        by_state.setdefault(abbr, {}).setdefault(year, []).append(
            {
                "number": record["disasterNumber"],
                "title": record["declarationTitle"].title(),
                "type": record["incidentType"],
                "declared": declared.isoformat(),
                "major": record["declarationType"] == "DR",
                "federal_obligated": int(summary.get("totalObligatedAmountPa") or 0),
                "individual_approved": int(summary.get("totalAmountIhpApproved") or 0),
            }
        )

    for years in by_state.values():
        for entries in years.values():
            entries.sort(key=lambda d: -d["federal_obligated"])
    return by_state


def _series(frame: pl.DataFrame, abbrs: list[str], years: list[int], value: str) -> list[list[int]]:
    """Pivot a long frame into states x years, filling gaps with 0."""
    lookup = {(row["abbr"], row["year"]): row[value] for row in frame.to_dicts()}
    return [[lookup.get((abbr, year), 0) for year in years] for abbr in abbrs]


def build_national(finances: pl.DataFrame, population: pl.DataFrame, deflator: pl.DataFrame) -> Path:
    """national.json: every state and year, columnar so the site fetches once."""
    years = list(YEARS)
    abbrs = [a for a in ABBRS_50 if a in set(finances["abbr"].to_list())]

    totals = (
        finances.filter(pl.col("flow").is_in(["revenue", "expenditure"]))
        .group_by(["abbr", "year", "flow"])
        .agg(pl.col("amount").sum())
    )
    by_function = (
        finances.filter(pl.col("flow") == "expenditure")
        .group_by(["abbr", "year", "function"])
        .agg(pl.col("amount").sum())
    )
    by_source = (
        finances.filter(pl.col("flow") == "revenue")
        .group_by(["abbr", "year", "component"])
        .agg(pl.col("amount").sum())
    )

    payload = {
        "years": years,
        "states": abbrs,
        "names": {abbr: NAME_BY_ABBR[abbr] for abbr in abbrs},
        "deflator": [
            deflator.filter(pl.col("year") == year)["deflator"].item() for year in years
        ],
        "population": _series(population, abbrs, years, "population"),
        "totals": {
            flow: _series(totals.filter(pl.col("flow") == flow), abbrs, years, "amount")
            for flow in ("revenue", "expenditure")
        },
        "expenditure_by_function": {
            function: _series(
                by_function.filter(pl.col("function") == function), abbrs, years, "amount"
            )
            for function in sorted(by_function["function"].unique().to_list())
        },
        "revenue_by_source": {
            component: _series(
                by_source.filter(pl.col("component") == component), abbrs, years, "amount"
            )
            for component in sorted(by_source["component"].unique().to_list())
        },
    }
    return write_json(OUT_DIR / "national.json", payload)


def load_state_gdp() -> dict[str, dict[int, float]]:
    """Nominal gross state product, keyed by state and calendar year."""
    raw = json.loads(fetch.state_gdp().read_text())
    return {abbr: {int(y): v for y, v in series.items()} for abbr, series in raw.items()}


def debt_burden(finances: pl.DataFrame) -> tuple[dict[str, dict[str, list[float]]], dict[str, list[float]]]:
    """Debt measured against revenue — the money a state actually controls.

    GDP is the size of the economy, but a state only taxes a slice of it, and
    that slice varies three-fold across states. Revenue is what is actually
    available to service debt, so it is the denominator that makes "is this a
    burden" answerable. Interest is the annual cost; principal repaid is not
    used, because much of it is refinancing rather than a call on the budget.

    Returns per-state series plus the 50-state median for each year.
    """
    years = list(YEARS)
    revenue = (
        finances.filter(pl.col("flow") == "revenue")
        .group_by(["abbr", "year"])
        .agg(pl.col("amount").sum().alias("revenue"))
    )
    interest = (
        finances.filter(
            (pl.col("flow") == "expenditure") & (pl.col("component") == "interest_on_debt")
        )
        .group_by(["abbr", "year"])
        .agg(pl.col("amount").sum().alias("interest"))
    )
    stock = (
        finances.filter(
            (pl.col("flow") == "debt") & (pl.col("component") == "outstanding_end")
        )
        .group_by(["abbr", "year"])
        .agg(pl.col("amount").sum().alias("debt"))
    )
    joined = revenue.join(interest, on=["abbr", "year"], how="left").join(
        stock, on=["abbr", "year"], how="left"
    )

    per_state: dict[str, dict[str, list[float]]] = {}
    for abbr in ABBRS_50:
        rows = joined.filter(pl.col("abbr") == abbr)
        lookup = {r["year"]: r for r in rows.to_dicts()}
        interest_share, debt_share = [], []
        for year in years:
            row = lookup.get(year)
            rev = (row or {}).get("revenue") or 0
            interest_share.append(round(((row or {}).get("interest") or 0) / rev, 5) if rev else 0.0)
            debt_share.append(round(((row or {}).get("debt") or 0) / rev, 4) if rev else 0.0)
        per_state[abbr] = {"interest_share": interest_share, "debt_share": debt_share}

    median = {"interest_share": [], "debt_share": []}
    for index in range(len(years)):
        for key in median:
            values = sorted(per_state[a][key][index] for a in ABBRS_50 if per_state[a][key][index])
            middle = len(values) // 2
            median[key].append(
                round(
                    values[middle]
                    if len(values) % 2
                    else (values[middle - 1] + values[middle]) / 2,
                    5,
                )
                if values
                else 0.0
            )
    return per_state, median


def build_states(
    finances: pl.DataFrame,
    population: pl.DataFrame,
    governors: pl.DataFrame,
    disasters: dict[str, dict[int, list[dict]]],
    gdp: dict[str, dict[int, float]] | None = None,
    burden: tuple[dict, dict] | None = None,
) -> list[Path]:
    """states/{abbr}.json: everything one state page needs, in one fetch."""
    years = list(YEARS)
    paths = []

    for abbr in ABBRS_50:
        state = finances.filter(pl.col("abbr") == abbr)
        if state.is_empty():
            continue

        def by(column: str, flow: str) -> dict[str, list[int]]:
            grouped = (
                state.filter(pl.col("flow") == flow)
                .group_by([column, "year"])
                .agg(pl.col("amount").sum())
            )
            out = {}
            for key in sorted(grouped[column].unique().to_list()):
                rows = grouped.filter(pl.col(column) == key)
                lookup = dict(zip(rows["year"].to_list(), rows["amount"].to_list()))
                out[key] = [lookup.get(year, 0) for year in years]
            return out

        debt = (
            state.filter(pl.col("flow") == "debt")
            .group_by(["component", "year"])
            .agg(pl.col("amount").sum())
        )
        debt_out = {}
        for component in sorted(debt["component"].unique().to_list()):
            rows = debt.filter(pl.col("component") == component)
            lookup = dict(zip(rows["year"].to_list(), rows["amount"].to_list()))
            debt_out[component] = [lookup.get(year, 0) for year in years]

        # Available only through FY2021: Census stopped reporting the split
        # when it dropped conduit debt.
        by_purpose = (
            state.filter((pl.col("flow") == "debt") & (pl.col("component") == "outstanding_end"))
            .group_by(["purpose", "year"])
            .agg(pl.col("amount").sum())
        )
        debt_by_purpose = {}
        for kind in sorted(by_purpose["purpose"].drop_nulls().unique().to_list()):
            rows_ = by_purpose.filter(pl.col("purpose") == kind)
            lookup_ = dict(zip(rows_["year"].to_list(), rows_["amount"].to_list()))
            debt_by_purpose[kind] = [lookup_.get(year, 0) for year in years]

        holdings_grouped = (
            state.filter(pl.col("flow") == "holdings")
            .group_by(["component", "year"])
            .agg(pl.col("amount").sum())
        )
        holdings = {}
        for component in sorted(holdings_grouped["component"].unique().to_list()):
            rows_ = holdings_grouped.filter(pl.col("component") == component)
            lookup_ = dict(zip(rows_["year"].to_list(), rows_["amount"].to_list()))
            holdings[component] = [lookup_.get(year, 0) for year in years]

        state_gdp = (gdp or {}).get(abbr, {})

        pop = population.filter(pl.col("abbr") == abbr)
        pop_lookup = dict(zip(pop["year"].to_list(), pop["population"].to_list()))

        by_function = by("function", "expenditure")
        by_component = by("component", "expenditure")
        revenue_by_source = by("component", "revenue")

        # What the capital money actually built. The construction, land and
        # equipment codes carry the same function digits as operating spending,
        # so capital can be broken out by purpose — which is the only way to
        # answer what borrowing pays for, since no source ties an individual
        # bond to an individual project.
        capital_rows = state.filter(
            (pl.col("flow") == "expenditure")
            & pl.col("component").map_elements(
                lambda c: categories.BUDGET_SIDE.get(c) == "capital", return_dtype=pl.Boolean
            )
        )
        capital_grouped = (
            capital_rows.group_by(["function", "year"]).agg(pl.col("amount").sum())
        )
        capital_by_function = {}
        for function in sorted(capital_grouped["function"].unique().to_list()):
            rows_ = capital_grouped.filter(pl.col("function") == function)
            lookup_ = dict(zip(rows_["year"].to_list(), rows_["amount"].to_list()))
            capital_by_function[function] = [lookup_.get(year, 0) for year in years]

        # Operating and capital move for different reasons and are funded
        # differently, so the page needs them apart rather than as one total.
        spending_split = {"operating": [0] * len(years), "capital": [0] * len(years)}
        for component, series in by_component.items():
            side = categories.BUDGET_SIDE.get(component)
            if side is None:
                continue
            for index, value in enumerate(series):
                spending_split[side][index] += value

        # Anomalies are looked for in the functional breakdown plus the headline
        # series, since a debt issuance spike is one of the most telling signals.
        watched = {
            # Operating and capital as their own series, so a reader can tell a
            # reallocation inside the operating budget from the kind of spending
            # that borrowing pays for.
            **{f"spending.{k}": v for k, v in spending_split.items()},
            **{f"expenditure.{k}": v for k, v in by_function.items()},
            **{f"revenue.{k}": v for k, v in revenue_by_source.items()},
            # Only new borrowing: debt retired and opening balances move for
            # accounting reasons rather than because anything happened.
            **{f"debt.{k}": v for k, v in debt_out.items() if k == "issued"},
        }
        budget_by_year = [sum(v[i] for v in by_function.values()) for i in range(len(years))]
        found = anomalies.detect(watched, years, budget_by_year)
        state_disasters = disasters.get(abbr, {})

        payload = {
            "abbr": abbr,
            "name": NAME_BY_ABBR[abbr],
            "years": years,
            "fiscal_year_start_month": anomalies.fiscal_year_starts().get(abbr, 7),
            "population": [pop_lookup.get(year, 0) for year in years],
            "expenditure_by_function": by_function,
            "expenditure_by_component": by_component,
            "spending_split": spending_split,
            "capital_by_function": capital_by_function,
            "debt_service": by_component.get("interest_on_debt", [0] * len(years)),
            "revenue_by_source": revenue_by_source,
            "debt": debt_out,
            "debt_by_purpose": debt_by_purpose,
            "holdings": holdings,
            "burden": (burden[0] if burden else {}).get(abbr, {}),
            "burden_median": burden[1] if burden else {},
            "gdp": [int(state_gdp.get(year, 0)) for year in years],
            "governors": [
                {k: v for k, v in term.items() if k != "abbr"}
                for term in governors.filter(pl.col("abbr") == abbr).to_dicts()
            ],
            "anomalies": anomalies.as_dicts(found),
            "disasters": {str(year): entries for year, entries in sorted(state_disasters.items())},
        }
        paths.append(write_json(OUT_DIR / "states" / f"{abbr}.json", payload))

    return paths


def build_geo() -> Path:
    """geo/us-states.json: TopoJSON of the 50 states + DC.

    us-atlas ships an Albers USA projection with Alaska and Hawaii already
    positioned as insets, so the site needs no runtime projection. TopoJSON is
    kept rather than expanded to GeoJSON — it is a third the size and the site
    already depends on topojson-client to expand it.
    """
    source = REPO_ROOT / "node_modules" / "us-atlas" / "states-albers-10m.json"
    payload = json.loads(source.read_text())
    # The nation outline is unused and is a third of the file.
    payload["objects"].pop("nation", None)
    return write_json(OUT_DIR / "geo" / "us-states.json", payload)


def build_sources() -> Path:
    """sources.json: provenance for the 'Sources & Methods' section."""
    retrieved = lambda path: (  # noqa: E731
        date.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else None
    )
    payload = [
        {
            "name": "Census Bureau — Annual Survey of State Government Finances",
            "url": "https://www.census.gov/programs-surveys/state.html",
            "vintage": f"FY{START_YEAR}–FY{END_YEAR}",
            "retrieved": retrieved(RAW_DIR / "census-finance" / f"{END_YEAR}.json"),
            "notes": (
                "Revenue by source, expenditure by function and debt outstanding. Totals are "
                "computed from the detail item codes on one consistent definition across all "
                "years — general revenue and expenditure, with insurance-trust flows (public "
                "pensions, unemployment and workers' compensation) reported separately — "
                "because Census changed what its own published totals include between FY2021 "
                "and FY2022. For FY2022 onward, where the definitions agree, these totals "
                "reproduce the published figures exactly for all 50 states. Census counts "
                "differ from state budget documents: they cover all funds and follow a common "
                "classification rather than each state's own budget categories."
            ),
        },
        {
            "name": "Census Bureau — State Population Totals",
            "url": "https://www.census.gov/programs-surveys/popest.html",
            "vintage": f"{START_YEAR}–{END_YEAR}",
            "retrieved": retrieved(RAW_DIR / "population" / "NST-EST2024-ALLDATA.csv"),
            "notes": "Vintage 2024 estimates, with intercensal estimates for 2000–2009.",
        },
        {
            "name": "BEA — GDP implicit price deflator (via FRED series A191RD3A086NBEA)",
            "url": "https://fred.stlouisfed.org/series/A191RD3A086NBEA",
            "vintage": f"{START_YEAR}–{END_YEAR}",
            "retrieved": retrieved(RAW_DIR / "deflator" / "gdp-deflator.csv"),
            "notes": f"Rebased so FY{END_YEAR} = 1.0; used for inflation-adjusted dollars.",
        },
        {
            "name": "Wikidata — governors of US states",
            "url": "https://query.wikidata.org/",
            "vintage": "Full history, filtered to terms ending 1995 or later",
            "retrieved": retrieved(RAW_DIR / "politics" / "governors.json"),
            "notes": (
                "Term dates and party. Party-switchers carry several party values in "
                "Wikidata and are resolved in curated/governor_overrides.csv."
            ),
        },
        {
            "name": "us-atlas — US state boundaries",
            "url": "https://github.com/topojson/us-atlas",
            "vintage": "10m, Albers USA projection",
            "retrieved": None,
            "notes": "Derived from the Census cartographic boundary files.",
        },
    ]
    return write_json(OUT_DIR / "sources.json", payload)


def build() -> list[Path]:
    finances = load_finances()
    population = load_population()
    governors = load_governors()
    return [
        build_national(finances, population, load_deflator()),
        *build_states(
            finances,
            population,
            governors,
            load_disasters(),
            load_state_gdp(),
            debt_burden(finances),
        ),
        build_politics(),
        build_geo(),
        build_sources(),
    ]


if __name__ == "__main__":
    for path in build():
        print(f"{path.relative_to(REPO_ROOT)}  {path.stat().st_size / 1024:.0f}KB")
