"""Credential handling — the one place a mistake leaks a secret."""

import httpx
import pytest

from state_budgets import fetch


@pytest.fixture(autouse=True)
def _clear_key_cache():
    fetch.census_api_key.cache_clear()
    yield
    fetch.census_api_key.cache_clear()


def test_environment_variable_wins_over_the_keychain(monkeypatch):
    monkeypatch.setenv("CENSUS_API_KEY", "from-env")
    assert fetch.census_api_key() == "from-env"


def test_missing_key_explains_how_to_store_one(monkeypatch):
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    # Simulate a machine with no `security` binary and so no Keychain.
    monkeypatch.setattr(fetch.subprocess, "run", _raise_file_not_found)

    with pytest.raises(RuntimeError, match="add-generic-password"):
        fetch.census_api_key()


def test_http_errors_do_not_leak_the_key():
    request = httpx.Request("GET", "https://api.census.gov/data?key=super-secret")
    response = httpx.Response(403, request=request)
    error = httpx.HTTPStatusError("403 for https://api.census.gov/data?key=super-secret", request=request, response=response)

    redacted = fetch._redact(str(error), {"key": "super-secret"})

    assert "super-secret" not in redacted
    assert "REDACTED" in redacted


def test_html_error_page_is_rejected_rather_than_cached():
    """The Census API answers a bad key with HTTP 200 and an HTML page, so
    without this guard an error page gets cached as if it were data."""
    body = "<html><head><title>Invalid Key</title></head><body>...</body></html>"

    with pytest.raises(RuntimeError, match="Invalid Key"):
        fetch._reject_non_json(body, "https://api.census.gov/data/timeseries/govsstatefin")


def test_valid_json_passes_through():
    fetch._reject_non_json('[["AMOUNT","ITEM_CODE"],["100","E12"]]', "https://example.test")


def _raise_file_not_found(*args, **kwargs):
    raise FileNotFoundError
