"""Item-code classification — the mapping the whole spending story rests on."""

from state_budgets import categories


def test_k12_aid_to_school_districts_is_counted_as_k12():
    """Most state K-12 money is passed to districts as aid (Q12), not spent
    directly (E12); missing this would understate K-12 several-fold."""
    assert categories.classify("Q12") == {
        "flow": "expenditure",
        "function": "k12",
        "component": "aid_to_school_districts",
    }
    assert categories.classify("E12")["function"] == "k12"


def test_medicaid_lands_in_public_welfare():
    """Census has no Medicaid line: it sits inside public welfare (E79)."""
    assert categories.classify("E79") == {
        "flow": "expenditure",
        "function": "public_welfare",
        "component": "current_operations",
    }


def test_same_function_digits_across_prefixes_agree():
    for code in ("E44", "F44", "M44"):
        assert categories.classify(code)["function"] == "transportation"


def test_federal_aid_is_revenue_not_expenditure():
    assert categories.classify("B79") == {
        "flow": "revenue",
        "function": "public_welfare",
        "component": "federal_aid",
    }


def test_debt_components_stay_separate():
    assert categories.classify("49U") == {
        "flow": "debt",
        "function": "long_term_debt",
        "component": "outstanding_end",
    }
    assert categories.classify("29U")["component"] == "issued"


def test_cash_and_security_holdings_are_excluded():
    """X/Z codes are asset holdings (a state's pension portfolio), not budget
    flows — counting them as revenue would multiply a state's budget."""
    for code in ("X30", "X40", "Z00", "Z01"):
        assert categories.classify(code) is None


def test_insurance_trust_is_kept_apart_from_the_general_budget():
    assert categories.classify("Y05")["flow"] == "insurance_trust"


def test_every_code_in_the_dictionary_has_a_description():
    descriptions = categories.descriptions()
    assert len(descriptions) > 200
    assert all(text for text in descriptions.values())
    assert descriptions["E79"] == "Welfare NEC-Current Operation"
