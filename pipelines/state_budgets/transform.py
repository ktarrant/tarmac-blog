"""Parse raw sources into tidy tables keyed by state and year, then write
the JSON the site reads from public/data/state-budgets/.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import polars as pl

from . import fetch
from .paths import END_YEAR, OUT_DIR, RAW_DIR, REPO_ROOT, START_YEAR, YEARS
from .states import ABBRS, NAME_BY_ABBR, STATES

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
                "Revenue by source, expenditure by function and debt outstanding. Census "
                "covers all funds, including insurance-trust and utility activity, so totals "
                "differ from budget documents."
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
    return [build_politics(), build_geo(), build_sources()]


if __name__ == "__main__":
    for path in build():
        print(f"{path.relative_to(REPO_ROOT)}  {path.stat().st_size / 1024:.0f}KB")
