"""Aethel Grid node registry and harmonic sync."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from config.quibidt_constants import (
    POWER_OF_SEVEN,
    VAULT_SECURITY_CLASS,
    BUSBAR_THERMAL_HALT_C,
)


class HarmonicState(enum.Enum):
    """Grid synchronization states."""

    SYNC = "sync"
    DRIFT = "drift"
    OFFLINE = "offline"


@dataclass
class GridNode:
    """Physical or logical node in the Aethel Grid."""

    node_id: str
    label: str
    location: str
    vault_class: int = 0
    busbar_halt_c: float = 0.0


NODE_001 = GridNode(
    node_id="NODE-001",
    label="Bethel Acres Vault",
    location="Bethel Acres, OK",
    vault_class=VAULT_SECURITY_CLASS,
)

NODE_002 = GridNode(
    node_id="NODE-002",
    label="48V DC Bus",
    location="Bethel Acres, OK",
    busbar_halt_c=BUSBAR_THERMAL_HALT_C,
)


class AethelGrid:
    """Registry of grid nodes with harmonic factor."""

    def __init__(self) -> None:
        self.nodes: dict[str, GridNode] = {}
        self.register(NODE_001)
        self.register(NODE_002)

    def register(self, node: GridNode) -> None:
        """Add a node to the grid."""
        self.nodes[node.node_id] = node

    def harmonic_factor(self) -> float:
        """Return the Power-of-Seven harmonic as a decimal."""
        return POWER_OF_SEVEN / 1000.0
