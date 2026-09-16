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
    "K": "equipment",
    "L": "aid_to_state_governments",
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
    # "Miscellaneous commercial activities, NEC" in Census's classification,
    # which explicitly covers state disaster insurance. It is where Florida's
    # post-Hurricane-Ian property insurance intervention lands, so it earns its
    # own category rather than disappearing into "other".
    "03": "commercial_and_insurance",
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
    "26": "administration",     # legislative bodies
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
    "54": "natural_resources",  # agriculture
    "55": "natural_resources",  # state fish and game
    "56": "natural_resources",  # federal and state forestry
    "59": "natural_resources",
    "60": "other",              # parking
    "61": "parks_and_recreation",
    "62": "public_safety",
    "66": "other",              # protective inspection
    "67": "public_welfare",     # federal categorical assistance programs
    "68": "public_welfare",     # other cash assistance
    "73": "public_welfare",
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

# Which side of the budget a kind of spending sits on. This is the distinction
# that makes state borrowing make sense: nearly every state must balance its
# operating budget, so operating spending tracks revenue year to year, while
# capital projects are paid for with bonds and are what the debt is actually
# for. Interest on that debt is an operating cost and is counted here as one;
# repaying principal is not an expense at all in Census terms, it retires a
# liability, which is why debt retired never appears in spending.
BUDGET_SIDE = {
    "current_operations": "operating",
    "aid_to_local": "operating",
    "aid_to_school_districts": "operating",
    "aid_to_state_governments": "operating",
    "aid_to_federal": "operating",
    "subsidies": "operating",
    "interest_on_debt": "operating",
    "construction": "capital",
    "capital_other": "capital",
    "equipment": "capital",
}

# Census leaves function 27 out of its published total expenditure (SF0132).
# Excluding it reproduces that total to the dollar for all 50 states; including
# it overstates spending by roughly half a percent. The function has no entry
# in the 2006 classification manual or the FY2024 documentation, so it is
# excluded on the strength of that reconciliation rather than a definition.
EXCLUDED_FROM_EXPENDITURE = {"27"}

# Debt and cash codes don't follow the prefix/function scheme.
#
# Long-term debt is reported in two tracks that must be added to reach Census's
# published total (SF0455). The classification manual names them: the T codes
# are "Public Debt For Private Purposes", which it notes is "often referred to
# as conduit debt" — borrowing a state issues on behalf of private borrowers
# (industrial revenue, pollution control, private hospitals and colleges) who
# repay it, and which is not really a burden on the state's taxpayers. The U
# codes are "Unspecified Public Purposes": the state's own debt.
#
# This is why the total steps down in FY2022. A GASB pronouncement said conduit
# debt with no guarantee from the issuer is not the issuer's liability, so
# Census dropped the T codes entirely; the guaranteed remainder was folded into
# the U series. Counting only U understates pre-2022 debt against the published
# total, and counting the total without saying what is in it overstates what
# states actually owe.
DEBT_CODES = {
    "19T": ("long_term_debt", "outstanding_beginning", "private_purpose"),
    "24T": ("long_term_debt", "issued", "private_purpose"),
    "34T": ("long_term_debt", "retired", "private_purpose"),
    "44T": ("long_term_debt", "outstanding_end", "private_purpose"),
    "19U": ("long_term_debt", "outstanding_beginning", "public_purpose"),
    "29U": ("long_term_debt", "issued", "public_purpose"),
    "39U": ("long_term_debt", "retired", "public_purpose"),
    "49U": ("long_term_debt", "outstanding_end", "public_purpose"),
    "61V": ("short_term_debt", "outstanding_beginning", "short_term"),
    "64V": ("short_term_debt", "outstanding_end", "short_term"),
}

# Cash and securities a state holds outside its pension funds: W01 is money set
# aside to service debt (sinking funds), W31 unspent bond proceeds, W61
# everything else. Together they are the closest thing Census reports to a state
# treasury, and they matter to the debt picture — a state owing $30B while
# holding $25B is in a different position than the debt figure alone suggests.
# Census stopped publishing all three from FY2022.
HOLDINGS_CODES = {
    "W01": "debt_offsets",
    "W31": "bond_funds",
    "W61": "other_funds",
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
        kind, component, purpose = DEBT_CODES[item_code]
        return {
            "flow": "debt",
            "function": kind,
            "component": component,
            "purpose": purpose,
        }

    if item_code in HOLDINGS_CODES:
        return {
            "flow": "holdings",
            "function": "cash_and_securities",
            "component": HOLDINGS_CODES[item_code],
            "purpose": None,
        }

    prefix, digits = item_code[0], item_code[1:]

    if prefix in INSURANCE_TRUST_PREFIXES:
        return {
            "flow": "insurance_trust",
            "function": "insurance_trust",
            "component": item_code,
            "purpose": None,
        }

    if prefix in SPENDING_PREFIXES:
        return {
            "flow": "expenditure_excluded" if digits in EXCLUDED_FROM_EXPENDITURE else "expenditure",
            "function": FUNCTIONS.get(digits, "other"),
            "component": SPENDING_PREFIXES[prefix],
            "purpose": None,
        }

    if prefix in REVENUE_PREFIXES:
        return {
            "flow": "revenue",
            "function": FUNCTIONS.get(digits, "other"),
            "component": REVENUE_PREFIXES[prefix],
            "purpose": None,
        }

    return None
