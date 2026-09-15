"""Download raw sources into data/raw/, caching by filename.

Every function here returns a Path to a file on disk and re-downloads only
when that file is missing, so reruns are cheap and offline-friendly. Nothing
here parses: see transform.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from .paths import RAW_DIR

USER_AGENT = "tarmac-blog-pipeline/0.1 (https://github.com/ktarrant/tarmac-blog)"

# Census finance data is published per year under the survey's table directory,
# with the filename varying by year (File/Files/file), so the year directory is
# listed rather than guessing a URL.
CENSUS_TABLES = "https://www2.census.gov/programs-surveys/gov-finances/tables"
CENSUS_API = "https://api.census.gov/data/timeseries/govsstatefin"
POPULATION_FILES = {
    # decade file -> years it covers
    "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv": range(2021, 2025),
    "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/state/totals/nst-est2020-alldata.csv": range(2010, 2021),
    "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/state/st-est00int-alldata.csv": range(2000, 2010),
}
DEFLATOR_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=A191RD3A086NBEA"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

GOVERNORS_QUERY = """
SELECT ?stateLabel ?person ?personLabel ?partyLabel ?start ?end WHERE {
  ?state wdt:P31 wd:Q35657 ; wdt:P1313 ?position .
  ?person p:P39 ?stmt .
  ?stmt ps:P39 ?position .
  # Restricts to real people: Wikidata also models fictional governors (The
  # West Wing). Must come after ?position binds or the query planner scans
  # every human and the endpoint 502s.
  ?person wdt:P31 wd:Q5 .
  OPTIONAL { ?stmt pq:P580 ?start . }
  OPTIONAL { ?stmt pq:P582 ?end . }
  OPTIONAL { ?person wdt:P102 ?party . }
  FILTER(!BOUND(?end) || ?end >= "1995-01-01T00:00:00Z"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def _download(url: str, dest: Path, *, params: dict | None = None) -> Path:
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        dest.write_bytes(response.content)
    return dest


def census_api_key() -> str:
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise RuntimeError(
            "CENSUS_API_KEY is not set. Get a free key at "
            "https://api.census.gov/data/key_signup.html and export it."
        )
    return key


def state_finances(year: int) -> Path:
    """State government finance items for one fiscal year, from the Census API.

    Returns the raw API JSON: rows of [AMOUNT, ITEM_CODE, AGG_DESC, CATEGORY, ...].
    """
    dest = RAW_DIR / "census-finance" / f"{year}.json"
    return _download(
        CENSUS_API,
        dest,
        params={
            "get": "AMOUNT,ITEM_CODE,AGG_DESC,CATEGORY,GOVTYPE",
            "for": "state:*",
            "time": str(year),
            "key": census_api_key(),
        },
    )


def population() -> list[Path]:
    """Census population estimates, one file per decade."""
    paths = []
    for url in POPULATION_FILES:
        paths.append(_download(url, RAW_DIR / "population" / url.rsplit("/", 1)[-1]))
    return paths


def gdp_deflator() -> Path:
    """Annual national GDP price deflator (BEA series, via FRED), index 2017=100."""
    return _download(DEFLATOR_URL, RAW_DIR / "deflator" / "gdp-deflator.csv")


def governors() -> Path:
    """Governor terms with party and dates, from Wikidata."""
    dest = RAW_DIR / "politics" / "governors.json"
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(
            WIKIDATA_SPARQL,
            params={"query": GOVERNORS_QUERY},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        dest.write_bytes(response.content)
    return dest


def fetch_all(years: range) -> None:
    for year in years:
        state_finances(year)
    population()
    gdp_deflator()
    governors()


if __name__ == "__main__":
    from .paths import YEARS

    fetch_all(YEARS)
    print(f"raw sources cached in {RAW_DIR}")
