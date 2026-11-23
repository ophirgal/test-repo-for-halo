"""Immutable ledger values and the ledger's data error."""

import datetime
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Transaction:
    """One ledger row, validated and typed."""

    id: str
    date: datetime.date
    amount: Decimal
    currency: str
    category: str
    memo: str


class LedgerError(Exception):
    """A ledger row or header that cannot be read, at its physical line."""

    def __init__(self, line, reason):
        super().__init__(line, reason)
        self.line = line
        self.reason = reason

    def __str__(self):
        return f"line {self.line}: {self.reason}"
