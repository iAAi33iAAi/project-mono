"""1440 Treasury with collateralization guard."""
from __future__ import annotations

from dataclasses import dataclass

from config.quibidt_constants import (
    COLLATERAL_TARGET,
    COLLATERAL_MIN,
)


class TreasuryHalt(Exception):
    """Raised when collateral ratio breaches minimum."""


@dataclass
class TreasurySnapshot:
    """Point-in-time view of treasury balances."""

    gold: float
    digital: float
    outstanding: float

    @property
    def ratio(self) -> float:
        if self.outstanding == 0:
            return float("inf")
        return (self.gold + self.digital) / self.outstanding


class Treasury:
    """Manages gold and digital reserves against outstanding obligations."""

    def __init__(self) -> None:
        self.gold = 0.0
        self.digital = 0.0
        self.outstanding = 0.0

    def deposit_gold(self, amount: float) -> None:
        self.gold += amount

    def deposit_digital(self, amount: float) -> None:
        self.digital += amount

    def disburse(self, amount: float) -> None:
        future = self.outstanding + amount
        assets = self.gold + self.digital
        if future > 0 and assets / future < COLLATERAL_MIN:
            raise TreasuryHalt(
                f"Collateral ratio {assets / future:.4f} "
                f"below minimum {COLLATERAL_MIN}"
            )
        self.outstanding = future

    def snapshot(self) -> TreasurySnapshot:
        return TreasurySnapshot(
            gold=self.gold,
            digital=self.digital,
            outstanding=self.outstanding,
        )
