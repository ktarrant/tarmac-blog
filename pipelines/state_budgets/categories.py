"""Maps Census finance item codes onto the buckets the article reports.

Census item codes are systematic: a letter prefix says what kind of flow it is
(E = current operations, F = construction, M = aid paid to local government,
and so on) and the trailing two digits say which government function it serves.
The same digits mean the same function across prefixes, so the function map
below is keyed on those digits rather than on 200-odd individual codes.

Descriptions for individual codes live in curated/census_item_codes.json,
extracted from the FY2024 Census technical documentation.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

CURATED = Path(__file__).resolve().parent / "curated"

# What kind of flow the prefix represents.
SPENDING_PREFIXES = {
    "E": "current_operations",
    "F": "construction",
    "G": "capital_other",
    "I": "interest_on_debt",
    "J": "subsidies",
    "M": "aid_to_local",
    "Q": "aid_to_school_districts",
    "S": "aid_to_federal",
}
REVENUE_PREFIXES = {
    "A": "charges",
    "B": "federal_aid",
    "C": "state_aid_received",
    "D": "local_aid_received",
    "T": "taxes",
    "U": "misc_general_revenue",
}

# Trailing digits -> reporting function.
FUNCTIONS = {
    "01": "transportation",     # air transportation
    "03": "other",
    "04": "corrections",
    "05": "corrections",
    "09": "k12",
    "10": "k12",
    "12": "k12",
    "16": "higher_education",
    "18": "higher_education",
    "19": "higher_education",   # scholarships and other subsidies
    "21": "education_other",
    "22": "other",              # employment security administration
    "23": "administration",
    "24": "public_safety",      # local fire protection
    "25": "administration",     # judicial and legal
    "29": "administration",
    "30": "administration",
    "31": "administration",
    "32": "health_and_hospitals",
    "36": "health_and_hospitals",
    "42": "health_and_hospitals",
    "44": "transportation",
    "45": "transportation",
    "46": "transportation",
    "50": "housing_and_community",
    "52": "other",              # libraries
    "59": "natural_resources",
    "60": "other",              # parking
    "61": "parks_and_recreation",
    "62": "public_safety",
    "66": "other",              # protective inspection
    "74": "public_welfare",
    "75": "public_welfare",
    "77": "public_welfare",
    "79": "public_welfare",
    "80": "utilities",          # sewerage
    "81": "utilities",          # solid waste
    "85": "other",              # veterans' assistance
    "87": "transportation",     # water transport and terminals
    "89": "other",
    "90": "utilities",          # liquor stores
    "91": "utilities",
    "92": "utilities",
    "93": "utilities",
    "94": "transportation",     # transit
}

# Debt and cash codes don't follow the prefix/function scheme.
DEBT_CODES = {
    "19U": ("long_term_debt", "outstanding_beginning"),
    "29U": ("long_term_debt", "issued"),
    "39U": ("long_term_debt", "retired"),
    "49U": ("long_term_debt", "outstanding_end"),
    "61V": ("short_term_debt", "outstanding_beginning"),
    "64V": ("short_term_debt", "outstanding_end"),
}

# The insurance-trust system (unemployment, workers' comp, pensions) is a
# separate flow from the general budget and is reported apart from it, so that
# pension contributions don't read as "spending" in the functional breakdown.
INSURANCE_TRUST_PREFIXES = {"Y"}


@cache
def descriptions() -> dict[str, str]:
    """Official Census short description for each item code."""
    return json.loads((CURATED / "census_item_codes.json").read_text())


def classify(item_code: str) -> dict[str, str] | None:
    """Sort one item code into a flow, function and description.

    Returns None for codes the article doesn't report (cash and security
    holdings, and anything unrecognized), so callers can ignore them.
    """
    if item_code in DEBT_CODES:
        kind, component = DEBT_CODES[item_code]
        return {"flow": "debt", "function": kind, "component": component}

    prefix, digits = item_code[0], item_code[1:]

    if prefix in INSURANCE_TRUST_PREFIXES:
        return {"flow": "insurance_trust", "function": "insurance_trust", "component": item_code}

    if prefix in SPENDING_PREFIXES:
        return {
            "flow": "expenditure",
            "function": FUNCTIONS.get(digits, "other"),
            "component": SPENDING_PREFIXES[prefix],
        }

    if prefix in REVENUE_PREFIXES:
        return {
            "flow": "revenue",
            "function": FUNCTIONS.get(digits, "other"),
            "component": REVENUE_PREFIXES[prefix],
        }

    return None
