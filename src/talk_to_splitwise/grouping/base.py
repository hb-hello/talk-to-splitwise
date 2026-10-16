from __future__ import annotations

from typing import Protocol

from talk_to_splitwise.models import GroupedExpense, Transaction


class GroupingStrategy(Protocol):
    """Decides which transactions get combined into one Splitwise expense.

    A Splitwise expense has a single cost and a single split, so only
    transactions that share the same payer, participants, and group can be
    merged together.
    """

    def group(self, transactions: list[Transaction]) -> list[GroupedExpense]: ...
