"""Item-code classification — the mapping the whole spending story rests on."""

from state_budgets import categories


def test_k12_aid_to_school_districts_is_counted_as_k12():
    """Most state K-12 money is passed to districts as aid (Q12), not spent
    directly (E12); missing this would understate K-12 several-fold."""
    assert categories.classify("Q12") == {
        "flow": "expenditure",
        "function": "k12",
        "component": "aid_to_school_districts",
        "guarantee": None,
    }
    assert categories.classify("E12")["function"] == "k12"


def test_medicaid_lands_in_public_welfare():
    """Census has no Medicaid line: it sits inside public welfare (E79)."""
    assert categories.classify("E79") == {
        "flow": "expenditure",
        "function": "public_welfare",
        "component": "current_operations",
        "guarantee": None,
    }


def test_same_function_digits_across_prefixes_agree():
    for code in ("E44", "F44", "M44"):
        assert categories.classify(code)["function"] == "transportation"


def test_federal_aid_is_revenue_not_expenditure():
    assert categories.classify("B79") == {
        "flow": "revenue",
        "function": "public_welfare",
        "component": "federal_aid",
        "guarantee": None,
    }


def test_debt_components_stay_separate():
    assert categories.classify("49U") == {
        "flow": "debt",
        "function": "long_term_debt",
        "component": "outstanding_end",
        "guarantee": "nonguaranteed",
    }
    assert categories.classify("29U")["component"] == "issued"


def test_total_debt_needs_both_the_guaranteed_and_nonguaranteed_tracks():
    """Census reports long-term debt in two tracks and its published total is
    their sum. Counting only the U codes understated every state's debt --
    Maryland FY2021 by $10.8B of $30.7B -- and made the FY2022 definition
    change look like debt had jumped 31% when it actually fell."""
    guaranteed = categories.classify("44T")
    nonguaranteed = categories.classify("49U")

    assert guaranteed["component"] == nonguaranteed["component"] == "outstanding_end"
    assert guaranteed["guarantee"] == "full_faith_and_credit"
    assert nonguaranteed["guarantee"] == "nonguaranteed"
    # The issued/retired pairs have to line up the same way or the flows are
    # counted on one track and the stock on two.
    assert categories.classify("24T")["component"] == categories.classify("29U")["component"]
    assert categories.classify("34T")["component"] == categories.classify("39U")["component"]


def test_tax_codes_are_not_mistaken_for_debt_codes():
    """T is the prefix for taxes and also the suffix for guaranteed debt."""
    assert categories.classify("T01")["flow"] == "revenue"
    assert categories.classify("44T")["flow"] == "debt"


def test_cash_and_security_holdings_are_excluded():
    """X/Z codes are asset holdings (a state's pension portfolio), not budget
    flows — counting them as revenue would multiply a state's budget."""
    for code in ("X30", "X40", "Z00", "Z01"):
        assert categories.classify(code) is None


def test_function_27_is_kept_out_of_the_expenditure_total():
    """Census omits function 27 from published total expenditure; including it
    overstates spending ~0.5% and breaks reconciliation against SF0132."""
    assert categories.classify("E27")["flow"] == "expenditure_excluded"
    assert categories.classify("M27")["flow"] == "expenditure_excluded"
    assert categories.classify("E44")["flow"] == "expenditure"


def test_insurance_trust_is_kept_apart_from_the_general_budget():
    assert categories.classify("Y05")["flow"] == "insurance_trust"


def test_every_code_in_the_dictionary_has_a_description():
    descriptions = categories.descriptions()
    assert len(descriptions) > 200
    assert all(text for text in descriptions.values())
    assert descriptions["E79"] == "Welfare NEC-Current Operation"
