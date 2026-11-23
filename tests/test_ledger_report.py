"""Unit tests for the monthly report (SCRUM-118 t2)."""

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from ledger import RATES, CategoryTotal, LedgerError, Transaction, monthly_report, parse_csv

SAMPLE = Path(__file__).resolve().parent / "fixtures" / "ledger" / "sample.csv"
D = Decimal


@pytest.fixture(scope="module")
def sample():
    return parse_csv(SAMPLE)


def txn(amount, currency="ILS", category="misc", day=1, id=None):
    return Transaction(id or f"x{amount}{category}{day}", datetime.date(2026, 3, day),
                       D(amount), currency, category, "")


def cats(report):
    return [(c.name, c.total, c.count) for c in report.categories]


def test_rates_constant():
    assert RATES == {"ILS": D("1"), "USD": D("3.70"), "EUR": D("4.00")}


# Scenario 9
def test_march_in_ils(sample):
    r = monthly_report(sample, "2026-03")
    assert (r.month, r.base, r.count) == ("2026-03", "ILS", 7)
    assert (r.income, r.expense, r.net) == (D("12925.00"), D("-3025.50"), D("9899.50"))
    assert str(r.income) == "12925.00"
    assert r.categories == [
        CategoryTotal("salary", D("12000.00"), 1),
        CategoryTotal("rent", D("-1500.00"), 1),
        CategoryTotal("freelance", D("925.00"), 1),
        CategoryTotal("groceries", D("-760.50"), 2),
        CategoryTotal("software", D("-444.00"), 1),
        CategoryTotal("travel", D("-321.00"), 1),
    ]


# Scenario 10
def test_march_in_usd(sample):
    r = monthly_report(sample, "2026-03", base="USD")
    assert r.base == "USD"
    assert (str(r.income), str(r.expense), str(r.net)) == ("3493.24", "-817.70", "2675.54")
    totals = {c.name: str(c.total) for c in r.categories}
    assert totals["salary"] == "3243.24"
    assert totals["freelance"] == "250.00"


# Scenario 11
def test_round_once_after_summing_half_even():
    assert monthly_report([txn("0.05")], "2026-03", base="EUR").income == D("0.01")
    three = [txn("0.05", day=d) for d in (1, 2, 3)]
    r = monthly_report(three, "2026-03", base="EUR")
    assert r.income == D("0.04")
    assert r.net == D("0.04")
    assert cats(r) == [("misc", D("0.04"), 3)]


def test_half_even_ties():
    # 0.125 -> 0.12 and 0.375 -> 0.38 (ties go to the even cent)
    assert monthly_report([txn("0.50")], "2026-03", base="EUR").income == D("0.12")
    assert monthly_report([txn("1.50")], "2026-03", base="EUR").income == D("0.38")


def test_figures_rounded_independently():
    r = monthly_report([txn("0.05", category="a"), txn("0.05", category="b")],
                       "2026-03", base="EUR")
    # each category 0.0125 -> 0.01, income 0.025 -> 0.02
    assert [c.total for c in r.categories] == [D("0.01"), D("0.01")]
    assert r.income == D("0.02")


# Scenario 12
def test_two_places_always():
    r = monthly_report([txn("5"), txn("-2")], "2026-03")
    assert (str(r.income), str(r.expense), str(r.net)) == ("5.00", "-2.00", "3.00")
    assert [str(c.total) for c in r.categories] == ["3.00"]


def test_no_negative_zero():
    r = monthly_report([txn("-0.01", category="tiny")], "2026-03", base="EUR")
    assert str(r.expense) == "0.00" and str(r.net) == "0.00"
    assert str(r.categories[0].total) == "0.00"
    r = monthly_report([txn("5", category="c"), txn("-5", category="c")], "2026-03")
    assert str(r.net) == "0.00" and str(r.categories[0].total) == "0.00"


def test_category_sums_both_signs():
    r = monthly_report([txn("10", category="c"), txn("-4", category="c")], "2026-03")
    assert cats(r) == [("c", D("6.00"), 2)]
    assert (r.income, r.expense) == (D("10.00"), D("-4.00"))


# Scenario 13
def test_top_n(sample):
    r = monthly_report(sample, "2026-03", top=2)
    assert [c.name for c in r.categories] == ["salary", "rent"]
    assert (r.count, r.income, r.expense, r.net) == (7, D("12925.00"), D("-3025.50"), D("9899.50"))
    assert len(monthly_report(sample, "2026-03", top=99).categories) == 6
    assert len(monthly_report(sample, "2026-03", top=None).categories) == 6
    assert len(monthly_report(sample, "2026-03", top=1).categories) == 1


# Scenario 14
def test_ties_ordered_by_name():
    r = monthly_report([txn("-7", category="zeta"), txn("7", category="alpha"),
                        txn("9", category="mid")], "2026-03")
    assert [c.name for c in r.categories] == ["mid", "alpha", "zeta"]


# Scenario 15
def test_empty_month(sample):
    r = monthly_report(sample, "2026-05")
    assert r.count == 0
    assert (r.income, r.expense, r.net) == (D("0.00"), D("0.00"), D("0.00"))
    assert all(str(x) == "0.00" for x in (r.income, r.expense, r.net))
    assert r.categories == []
    assert r.to_dict() == {"month": "2026-05", "base": "ILS", "count": 0, "income": "0.00",
                           "expense": "0.00", "net": "0.00", "categories": []}


def test_to_dict(sample):
    d = monthly_report(sample, "2026-03", base="USD", top=1).to_dict()
    assert d == {"month": "2026-03", "base": "USD", "count": 7, "income": "3493.24",
                 "expense": "-817.70", "net": "2675.54",
                 "categories": [{"name": "salary", "total": "3243.24", "count": 1}]}


# Scenario 16
def test_only_the_month_counts(sample):
    r = monthly_report(sample, "2026-02")
    assert cats(r) == [("groceries", D("-99.99"), 1)]
    assert r.count == 1
    assert cats(monthly_report(sample, "2026-04")) == [("groceries", D("-50.00"), 1)]


# Scenario 17
def test_rates_parameter():
    rates = {"ILS": D(1), "USD": D(2), "EUR": D(4)}
    assert monthly_report([txn("10", "USD")], "2026-03", rates=rates).income == D("20.00")


# Scenario 18
@pytest.mark.parametrize("month", ["2026-3", "2026-13", "2026-00", "March 2026", "202603", "",
                                   "2026-03 ", "２０２６-03", None])
def test_bad_month_is_value_error(sample, month):
    with pytest.raises(ValueError) as info:
        monthly_report(sample, month)
    assert not isinstance(info.value, LedgerError)


def test_bad_base_and_top(sample):
    with pytest.raises(ValueError):
        monthly_report(sample, "2026-03", base="GBP")
    with pytest.raises(ValueError):
        monthly_report(sample, "2026-03", base="ILS", rates={"USD": D(1)})
    for top in (0, -1):
        with pytest.raises(ValueError):
            monthly_report(sample, "2026-03", top=top)


def test_missing_rate_for_counted_transaction():
    rates = {"ILS": D(1)}
    with pytest.raises(ValueError, match="USD"):
        monthly_report([txn("10", "USD")], "2026-03", rates=rates)
    # an uncounted transaction (other month) does not need a rate
    other = Transaction("o", datetime.date(2026, 4, 1), D("1"), "USD", "c", "")
    assert monthly_report([other], "2026-03", rates=rates).count == 0


def test_repeatable(sample):
    assert monthly_report(sample, "2026-03", base="EUR") == monthly_report(sample, "2026-03", base="EUR")


def test_accepts_any_iterable(sample):
    assert monthly_report(iter(sample), "2026-03") == monthly_report(sample, "2026-03")
