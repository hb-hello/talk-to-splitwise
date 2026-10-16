from __future__ import annotations

from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field, field_validator


class Transaction(BaseModel):
    """A single expense/line item, before grouping, to be posted to Splitwise.

    ``amount`` is split equally among ``participants``. Include ``paid_by`` in
    ``participants`` if the payer also owes a share of the cost.
    """

    description: str
    amount: Decimal = Field(gt=0)
    date: Date
    paid_by: int
    participants: list[int] = Field(min_length=1)
    category: str | None = None
    group_id: int | None = None

    @field_validator("participants")
    @classmethod
    def _no_duplicate_participants(cls, participants: list[int]) -> list[int]:
        if len(participants) != len(set(participants)):
            raise ValueError("participants must not contain duplicate user IDs")
        return participants

    def split_shares(self) -> dict[int, Decimal]:
        """Equal split of amount among participants, exact to the cent.

        Rounding remainder (if amount doesn't divide evenly) is distributed
        one cent at a time to the first participants, so shares sum exactly
        to ``amount``.
        """
        n = len(self.participants)
        total_cents = int((self.amount * 100).to_integral_value(rounding=ROUND_HALF_UP))
        base_cents, remainder = divmod(total_cents, n)
        shares: dict[int, Decimal] = {}
        for i, user_id in enumerate(self.participants):
            share_cents = base_cents + (1 if i < remainder else 0)
            shares[user_id] = Decimal(share_cents) / 100
        return shares


class GroupedExpense(BaseModel):
    """A single Splitwise expense merged from one or more source transactions
    that share the same payer, participants, and group."""

    expense: Transaction
    sources: list[Transaction]
