"""Monthly report: fixed-rate conversion, round-once half-even, top-N."""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

RATES = {"ILS": Decimal("1"), "USD": Decimal("3.70"), "EUR": Decimal("4.00")}
"""Fixed exchange rates, in ILS per unit of each currency. Never fetched."""

_MONTH_RE = re.compile(r"[0-9]{4}-(?:0[1-9]|1[0-2])")
_CENT = Decimal("0.01")
_ZERO = Decimal("0.00")


def check_month(month):
    """Return ``month`` if it is ``YYYY-MM`` with a month of 01-12, else raise ValueError."""
    if not isinstance(month, str) or not _MONTH_RE.fullmatch(month):
        raise ValueError(f"month {month!r} is not YYYY-MM")
    return month


def _money(value):
    """Quantize an exact sum once to two places, half to even, never -0.00."""
    rounded = value.quantize(_CENT, rounding=ROUND_HALF_EVEN)
    return rounded if rounded else _ZERO


@dataclass(frozen=True)
class CategoryTotal:
    name: str
    total: Decimal
    count: int


@dataclass(frozen=True)
class MonthlyReport:
    month: str
    base: str
    count: int
    income: Decimal
    expense: Decimal
    net: Decimal
    categories: list

    def to_dict(self):
        return {
            "month": self.month,
            "base": self.base,
            "count": self.count,
            "income": str(self.income),
            "expense": str(self.expense),
            "net": str(self.net),
            "categories": [
                {"name": c.name, "total": str(c.total), "count": c.count}
                for c in self.categories
            ],
        }


def monthly_report(transactions, month, base="ILS", top=None, rates=RATES):
    """Total one month's transactions by category in ``base`` currency."""
    check_month(month)
    if base not in rates:
        raise ValueError(f"unknown base currency {base!r}")
    if top is not None and top < 1:
        raise ValueError(f"top must be at least 1, got {top!r}")

    income = expense = net = Decimal(0)
    sums = {}
    counts = {}
    count = 0
    for t in transactions:
        if t.date.strftime("%Y-%m") != month:
            continue
        if t.currency not in rates:
            raise ValueError(f"no rate for currency {t.currency!r}")
        value = t.amount * rates[t.currency] / rates[base]
        count += 1
        net += value
        if value > 0:
            income += value
        else:
            expense += value
        sums[t.category] = sums.get(t.category, Decimal(0)) + value
        counts[t.category] = counts.get(t.category, 0) + 1

    categories = sorted(
        (CategoryTotal(name, _money(total), counts[name]) for name, total in sums.items()),
        key=lambda c: (-abs(c.total), c.name),
    )
    if top is not None:
        categories = categories[:top]
    return MonthlyReport(
        month=month,
        base=base,
        count=count,
        income=_money(income),
        expense=_money(expense),
        net=_money(net),
        categories=categories,
    )
