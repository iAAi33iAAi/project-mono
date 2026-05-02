"""MANNA Colony -- corporate siphon accounting."""
from __future__ import annotations

from dataclasses import dataclass, field

from config.quibidt_constants import (
    CORPORATE_SIPHON_RATE,
    ARCHITECT_CONSTANT,
)


@dataclass
class Transaction:
    """Single MANNA transaction with siphon split."""

    gross: float
    corporate: bool = False
    siphon: float = field(init=False)
    human_share: float = field(init=False)
    technology_share: float = field(init=False)

    def __post_init__(self) -> None:
        if self.corporate:
            self.siphon = self.gross * CORPORATE_SIPHON_RATE
        else:
            self.siphon = 0.0
        net = self.gross - self.siphon
        self.technology_share = net * ARCHITECT_CONSTANT
        self.human_share = net - self.technology_share


class MANNAKernel:
    """Processes transactions and tracks running totals."""

    def __init__(self) -> None:
        self.ledger: list[Transaction] = []

    def process(self, gross: float, corporate: bool = False) -> Transaction:
        """Record a transaction and return it."""
        tx = Transaction(gross=gross, corporate=corporate)
        self.ledger.append(tx)
        return tx

    def totals(self) -> dict[str, float]:
        """Aggregate totals across the ledger."""
        return {
            "gross": sum(t.gross for t in self.ledger),
            "siphoned": sum(t.siphon for t in self.ledger),
            "human": sum(t.human_share for t in self.ledger),
            "technology": sum(t.technology_share for t in self.ledger),
        }
