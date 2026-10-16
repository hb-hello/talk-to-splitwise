from __future__ import annotations

from decimal import Decimal

from talk_to_splitwise.models import GroupedExpense, Transaction

_GroupKey = tuple[int, frozenset[int], int | None]


class ByPayerAndSplit:
    """Default grouping strategy: merges transactions that share the same
    payer, the same set of participants, and the same Splitwise group.

    Amounts are summed and descriptions concatenated; the merged expense
    takes the date of the first transaction in the group.
    """

    def group(self, transactions: list[Transaction]) -> list[GroupedExpense]:
        buckets: dict[_GroupKey, list[Transaction]] = {}
        order: list[_GroupKey] = []
        for txn in transactions:
            key: _GroupKey = (txn.paid_by, frozenset(txn.participants), txn.group_id)
            if key not in buckets:
                buckets[key] = []
                order.append(key)
            buckets[key].append(txn)

        grouped: list[GroupedExpense] = []
        for key in order:
            sources = buckets[key]
            paid_by, participants, group_id = key
            merged = Transaction(
                description="; ".join(txn.description for txn in sources),
                amount=sum((txn.amount for txn in sources), start=Decimal("0")),
                date=sources[0].date,
                paid_by=paid_by,
                participants=sorted(participants),
                group_id=group_id,
            )
            grouped.append(GroupedExpense(expense=merged, sources=sources))
        return grouped
