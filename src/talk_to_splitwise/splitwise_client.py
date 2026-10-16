from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from decimal import Decimal

from splitwise import Splitwise
from splitwise.expense import Expense
from splitwise.user import ExpenseUser

from talk_to_splitwise.models import GroupedExpense, Transaction

logger = logging.getLogger(__name__)


@dataclass
class FriendInfo:
    id: int
    first_name: str | None
    last_name: str | None


@dataclass
class GroupInfo:
    id: int
    name: str
    member_ids: list[int] = field(default_factory=list)


@dataclass
class PostResult:
    description: str
    amount: str
    source_transaction_count: int
    dry_run: bool
    expense_id: int | None = None
    error: str | None = None


def _expense_users(txn: Transaction) -> list[tuple[int, Decimal, Decimal]]:
    """(user_id, paid_share, owed_share) for every user involved in the expense."""
    shares = txn.split_shares()
    entries = [
        (user_id, txn.amount if user_id == txn.paid_by else Decimal("0"), owed)
        for user_id, owed in shares.items()
    ]
    if txn.paid_by not in shares:
        entries.append((txn.paid_by, txn.amount, Decimal("0")))
    return entries


class SplitwiseClient:
    """Thin wrapper around the Splitwise SDK.

    In dry-run mode, no network calls are made: reads return empty results
    and posting logs the would-be API payload instead of calling
    ``createExpense``.
    """

    def __init__(self, *, dry_run: bool = False):
        self.dry_run = dry_run
        self._sdk: Splitwise | None = None
        if not dry_run:
            self._sdk = Splitwise(
                "",
                "",
                api_key=os.environ["SPLITWISE_API_KEY"],
            )

    def list_friends(self) -> list[FriendInfo]:
        if self.dry_run:
            logger.info("[dry-run] getFriends() skipped, no live Splitwise call made")
            return []
        return [FriendInfo(f.getId(), f.getFirstName(), f.getLastName()) for f in self._sdk.getFriends()]

    def list_groups(self) -> list[GroupInfo]:
        if self.dry_run:
            logger.info("[dry-run] getGroups() skipped, no live Splitwise call made")
            return []
        return [
            GroupInfo(g.getId(), g.getName(), [m.getId() for m in g.getMembers()])
            for g in self._sdk.getGroups()
        ]

    def post_expense(self, grouped: GroupedExpense) -> PostResult:
        txn = grouped.expense
        users = _expense_users(txn)

        if self.dry_run:
            logger.info(
                "[dry-run] createExpense: description=%r cost=%s group_id=%s date=%s users=%s "
                "(merged from %d source transaction(s))",
                txn.description,
                txn.amount,
                txn.group_id,
                txn.date,
                [(uid, f"paid={p}", f"owed={o}") for uid, p, o in users],
                len(grouped.sources),
            )
            return PostResult(
                description=txn.description,
                amount=str(txn.amount),
                source_transaction_count=len(grouped.sources),
                dry_run=True,
            )

        expense = Expense()
        expense.setCost(str(txn.amount))
        expense.setDescription(txn.description)
        expense.setDate(txn.date.isoformat())
        if txn.group_id is not None:
            expense.setGroupId(txn.group_id)

        expense_users = []
        for user_id, paid_share, owed_share in users:
            eu = ExpenseUser()
            eu.setId(user_id)
            eu.setPaidShare(str(paid_share))
            eu.setOwedShare(str(owed_share))
            expense_users.append(eu)
        expense.setUsers(expense_users)

        created, errors = self._sdk.createExpense(expense)
        if errors:
            logger.error("Splitwise rejected expense %r: %s", txn.description, errors.getErrors())
            return PostResult(
                description=txn.description,
                amount=str(txn.amount),
                source_transaction_count=len(grouped.sources),
                dry_run=False,
                error=str(errors.getErrors()),
            )

        logger.info("Posted expense %r as Splitwise expense id=%s", txn.description, created.getId())
        return PostResult(
            description=txn.description,
            amount=str(txn.amount),
            source_transaction_count=len(grouped.sources),
            dry_run=False,
            expense_id=created.getId(),
        )
